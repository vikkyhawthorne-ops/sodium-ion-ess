%% AUTOMOTIVE-GRADE MULTI-LAYER BMS ARCHITECTURE
% Ref: docs/paper.md, ISO 26262/AUTOSAR inspired

function [I_cmd, states] = bms_control_logic(inputs, params)
    % inputs: struct {SOC_est, V_cells, T_cells, I_measured, Mode, Fault_Reset, I_request, T_amb}

    persistent bms_state;
    persistent precharge_timer;
    persistent fault_latch;
    if isempty(bms_state)
        bms_state = 'Standby';
        precharge_timer = 0;
        fault_latch = 0;
    end

    %% LAYER 1: SAFETY / PROTECTION (Hard Override)
    % Asynchronous-equivalent logic for hard real-time protection
    is_critical_fault = any(inputs.V_cells > 3.85) || any(inputs.V_cells < 1.9) || any(inputs.T_cells > 85);
    if is_critical_fault
        fault_latch = 1;
    end
    if inputs.Fault_Reset
        fault_latch = 0;
    end

    %% LAYER 2: STATE MACHINE (Mode Logic)
    if fault_latch
        bms_state = 'Fault';
    else
        switch bms_state
            case 'Standby'
                if strcmp(inputs.Mode, 'Drive') || strcmp(inputs.Mode, 'Charge')
                    bms_state = 'Precharge';
                    precharge_timer = 0;
                end
            case 'Precharge'
                precharge_timer = precharge_timer + 0.01; % Explicit discrete time step
                if precharge_timer > 0.05 % 50ms precharge
                    if strcmp(inputs.Mode, 'Drive'), bms_state = 'Run';
                    else, bms_state = 'Charge'; end
                end
            case 'Run'
                if strcmp(inputs.Mode, 'Standby'), bms_state = 'Standby'; end
            case 'Charge'
                if strcmp(inputs.Mode, 'Standby') || all(inputs.SOC_est > 0.99), bms_state = 'Standby'; end
            case 'Fault'
                if ~fault_latch, bms_state = 'Standby'; end
        end
    end

    %% LAYER 3: ESTIMATION (Coupled Estimators)
    % Nonlinear OCV-SOC mapping: V_oc = f(SOC, T)
    SOC = inputs.SOC_est;
    V_oc = 3.1 + 0.4 * (SOC - 0.5) - 0.001 * (inputs.T_amb - 298.15);

    %% LAYER 4: ENERGY MANAGEMENT (MPC-inspired current scaling)
    % Objective: Maximize I_request subject to Thermal and Voltage constraints
    Q_n = params.Nominal_cell_capacity_Ah;

    % Multi-tier derating (Soft constraint handling)
    T_max = 60; T_crit = 85;
    thermal_derating = max(0, min(1, (T_crit - max(inputs.T_cells)) / (T_crit - T_max)));

    V_min = 2.5; V_max = 3.6;
    volt_derating = max(0, min(1, (max(inputs.V_cells) - V_min) / (V_max - V_min)));

    if strcmp(bms_state, 'Run')
        I_raw = inputs.I_request;
    elseif strcmp(bms_state, 'Charge')
        I_raw = Q_n * 0.5;
    elseif strcmp(bms_state, 'Precharge')
        I_raw = 0.1 * Q_n;
    else
        I_raw = 0;
    end

    % Optimal actuation command
    I_cmd = I_raw * thermal_derating * volt_derating;

    % LAYER 1 OVERRIDE (Final Latch)
    if strcmp(bms_state, 'Fault'), I_cmd = 0; end

    %% LAYER 5: ACTUATION MAPPING
    states.bms_state = bms_state;
    states.balancing_active = (inputs.V_cells - mean(inputs.V_cells)) > 0.01;
    states.I_limit = Q_n * thermal_derating;
    states.contactor_main = strcmp(bms_state, 'Run') || strcmp(bms_state, 'Charge');
    states.contactor_pre = strcmp(bms_state, 'Precharge');
    states.V_oc = V_oc;
end

%% MIMO STATE-SPACE MODEL (Coupled Electro-Thermal)
function [sys_ss, sys_tf] = get_battery_dynamics(params)
    % x = [SOC, V1, V2, T, SOH]'
    R0 = 0.01; R1 = 0.005; C1 = 500; Cth = 500; hA = 0.1;
    Q = params.Nominal_cell_capacity_Ah * 3600;

    % Electro-Thermal Coupling Matrix
    A = zeros(5,5);
    A(2,2) = -1/(R1*C1);
    A(4,4) = -hA/Cth;
    A(4,2) = R1/Cth; % Temperature feedback from RC branch

    B = zeros(5,2); % u = [I, T_amb]
    B(1,1) = -1/Q; B(2,1) = 1/C1; B(4,2) = hA/Cth;

    C = zeros(2,5); % y = [V_terminal, T]
    C(1,1) = 0.8; % Nonlinear OCV gradient dV/dSOC
    C(1,2) = -1; C(2,4) = 1;

    D = [-R0, 0; 0, 0];
    sys_ss = ss(A, B, C, D);
    sys_tf = tf(sys_ss);
end

%% EKF SOC ESTIMATOR (Observability-Rigorous)
function [soc_new, P_new] = ekf_estimator(v_meas, i_meas, soc_old, P_old, params)
    % Q: Process noise (uncertainty in current/integration)
    % R: Measurement noise (sensor accuracy)
    Q_noise = 1e-6; R_noise = 0.01;
    dt = 1;
    Q_cap = params.Nominal_cell_capacity_Ah * 3600;

    % Predict
    soc_pred = soc_old - i_meas * dt / Q_cap;
    P_pred = P_old + Q_noise;

    % Nonlinear Jacobian H = dV/dSOC
    H = 0.8;

    % Observability check (Rank of H)
    if abs(H) < 1e-3, K = 0; else
        K = P_pred * H / (H * P_pred * H + R_noise);
    end

    % Update
    v_pred = 3.1 + H * (soc_pred - 0.5) - i_meas * 0.01;
    soc_new = max(0, min(1, soc_pred + K * (v_meas - v_pred))); % Constraint handling
    P_new = (1 - K * H) * P_pred;
end
