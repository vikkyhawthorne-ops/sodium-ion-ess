%% SIMULINK BMS CONTROL SYSTEM MODEL (ECU Logic)
% Ref: docs/paper.md

function [I_cmd, states] = bms_control_logic(inputs, params)
    % inputs: struct {SOC_est, V_cells, T_cells, I_measured, Mode, Fault_Reset, I_request}

    persistent bms_state;
    persistent precharge_timer;
    if isempty(bms_state)
        bms_state = 'Standby';
        precharge_timer = 0;
    end

    %% 1. STATE MACHINE SIGNAL FLOW (Stateflow Logic)
    % Inputs: inputs.Mode, inputs.V_cells, inputs.T_cells
    % Transitions: governed by logical conditions
    % Outputs: states.contactor_main, states.contactor_pre, I_cmd_raw

    is_fault = any(inputs.V_cells > 3.8) || any(inputs.V_cells < 2.0) || any(inputs.T_cells > 85);

    % Transition Logic
    if is_fault
        bms_state = 'Fault';
    end

    switch bms_state
        case 'Standby'
            if inputs.Fault_Reset, bms_state = 'Standby'; end
            if strcmp(inputs.Mode, 'Drive') || strcmp(inputs.Mode, 'Charge')
                bms_state = 'Precharge';
                precharge_timer = 0;
            end
        case 'Precharge'
            precharge_timer = precharge_timer + 1;
            if precharge_timer > 5
                if strcmp(inputs.Mode, 'Drive'), bms_state = 'Driving';
                else, bms_state = 'Charging'; end
            end
        case 'Driving'
            if strcmp(inputs.Mode, 'Standby'), bms_state = 'Standby'; end
        case 'Charging'
            if strcmp(inputs.Mode, 'Standby') || all(inputs.SOC_est > 0.99), bms_state = 'Standby'; end
        case 'Fault'
            if inputs.Fault_Reset, bms_state = 'Standby'; end
    end

    %% 2. MIMO CONTROLLER
    Q_n = params.Nominal_cell_capacity_Ah;
    I_max_thermal = Q_n * exp(-0.5 * (max(inputs.T_cells) - 25)/20);

    if strcmp(bms_state, 'Driving'), I_cmd = inputs.I_request;
    elseif strcmp(bms_state, 'Charging'), I_cmd = Q_n * 0.5;
    elseif strcmp(bms_state, 'Precharge'), I_cmd = 0.1 * Q_n;
    else, I_cmd = 0;
    end

    I_cmd = min(I_cmd, I_max_thermal);
    if strcmp(bms_state, 'Fault'), I_cmd = 0; end

    % Output Signals
    states.bms_state = bms_state;
    states.balancing_active = (inputs.V_cells - mean(inputs.V_cells)) > 0.01;
    states.I_limit = I_max_thermal;
    states.contactor_main = strcmp(bms_state, 'Driving') || strcmp(bms_state, 'Charging');
    states.contactor_pre = strcmp(bms_state, 'Precharge');
end

%% SIMSCAPE-EQUIVALENT PLANT MODEL (Physical System)
% This section represents the Simscape implementation of the physical battery system.
% Components:
% - Battery Pack: Series connection of 16 cells (16S1P configuration).
% - Thermal Layout: Simscape Thermal domain modeling heat exchange and convection.
% - Pre-charge/Recharge Circuitry: Resistive path for safe connection.
% - Contactors: Physical switching hardware (Main and Pre-charge).

function [V_out, T_out] = plant_model(I_in, T_amb, params)
    % Electrical Domain (Simscape Equivalent Circuit)
    % V_terminal = OCV(SOC) - I*R_internal - V_rc1 - V_rc2
    R_int = params.Contact_resistance_Ohm + 0.01;
    V_out = 3.2 - I_in * R_int; % Simplified output for analysis

    % Thermal Domain (Simscape Heat Transfer)
    % Q = I^2 * R + Q_reversible
    C_th = 500; % [J/K] Thermal mass
    hA = 0.1;   % [W/K] Convection coefficient
    T_out = T_amb + (I_in^2 * R_int) / C_th - (hA/C_th)*(25 - T_amb);
end

%% STATE-SPACE PLANT MODEL (MIMO)
% x = [SOC, V1, V2, T, SOH]'
% u = [I, T_amb]'
% y = [V_terminal, T]'
function [sys_ss, sys_tf] = get_battery_dynamics(params)
    % linearized around SOC=0.5, T=25C
    R0 = 0.01; R1 = 0.005; C1 = 500; R2 = 0.002; C2 = 2000;
    Q = params.Nominal_cell_capacity_Ah * 3600;
    Cth = 500; hA = 0.1;

    A = zeros(5,5);
    A(2,2) = -1/(R1*C1);
    A(3,3) = -1/(R2*C2);
    A(4,4) = -hA/Cth;

    B = zeros(5,2);
    B(1,1) = -1/Q; B(2,1) = 1/C1; B(3,1) = 1/C2; B(4,2) = hA/Cth;

    C = zeros(2,5);
    C(1,1) = 0.5; C(1,2) = -1; C(1,3) = -1; C(2,4) = 1;

    D = [-R0, 0; 0, 0];

    % Using Control System Toolbox functions
    try
        sys_ss = ss(A, B, C, D);
        sys_tf = tf(sys_ss);
    catch
        % Fallback for environments without Control System Toolbox
        sys_ss = struct('A', A, 'B', B, 'C', C, 'D', D);
        sys_tf = 'TF_Requires_Control_Toolbox';
    end
end

%% SOC ESTIMATOR (EKF)
function [soc_new, P_new] = ekf_estimator(v_meas, i_meas, soc_old, P_old, params)
    dt = 1;
    Q = params.Nominal_cell_capacity_Ah * 3600;
    R = 0.01;
    soc_pred = soc_old - i_meas * dt / Q;
    P_pred = P_old + 1e-6;
    H = 0.5;
    K = P_pred * H / (H * P_pred * H + 0.01);
    v_pred = 3.2 + H * (soc_pred - 0.5) - i_meas * R;
    soc_new = soc_pred + K * (v_meas - v_pred);
    P_new = (1 - K * H) * P_pred;
end
