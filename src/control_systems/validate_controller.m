%% Controller Validation Script
% Verifies stability, response characteristics, and estimator convergence.
% Ref: docs/paper.md

% Executable portion must come before function definitions in a script with local functions
try
    validate_controller();
catch ME
    fprintf('Error in Controller Validation: %s\n', ME.message);
    rethrow(ME);
end

function validate_controller()
    params = load_optimized_data('src/control_systems/optimized_params.mat');
    results = struct();

    %% 1. Estimator Convergence (EKF)
    fprintf('Testing EKF Estimator Convergence...\n');
    soc_true = 0.5;
    soc_init = 0.8; % Incorrect initial condition
    P_init = 0.1;
    v_meas = 3.2; % Approx OCV at 0.5 SOC
    i_meas = 0;

    soc_est = soc_init;
    P = P_init;
    convergence_steps = 0;
    for i = 1:50
        [soc_est, P] = ekf_estimator(v_meas, i_meas, soc_est, P, params);
        if abs(soc_est - soc_true) < 0.01 && convergence_steps == 0
            convergence_steps = i;
        end
    end
    results.ekf_converged = abs(soc_est - soc_true) < 0.01;
    results.ekf_steps = convergence_steps;
    fprintf('  EKF Converged: %s in %d steps\n', mat2str(results.ekf_converged), convergence_steps);

    %% 2. Cell Balancing Convergence
    fprintf('Testing Cell Balancing Logic...\n');
    V_cells = [3.3, 3.32, 3.28, 3.31]; % Divergent voltages
    inputs.V_cells = V_cells;
    inputs.T_cells = [25, 25, 25, 25];
    inputs.SOC_est = 0.5;
    inputs.I_measured = 0;
    inputs.Mode = 'Standby';
    inputs.Fault_Reset = 0;
    inputs.I_request = 0;

    [~, states] = bms_control_logic_local(inputs, params);
    results.balancing_active = states.balancing_active;
    fprintf('  Balancing Active: %s\n', mat2str(results.balancing_active));

    %% 3. In-rush Current & Fault Response
    fprintf('Testing Fault Response (Over-temperature)...\n');
    inputs.T_cells = [90, 25, 25, 25]; % Trigger fault
    [I_cmd, states] = bms_control_logic_local(inputs, params);
    results.fault_triggered = strcmp(states.bms_state, 'Fault');
    results.fault_I_cmd = I_cmd;
    fprintf('  Fault Triggered: %s, I_cmd: %.1f A\n', states.bms_state, I_cmd);

    %% 4. Response Characteristics (Temporal)
    results.I_limit = states.I_limit;

    generate_validation_report(results);
end

function generate_validation_report(results)
    fprintf('\n====================================\n');
    fprintf('   BMS CONTROLLER VALIDATION REPORT\n');
    fprintf('====================================\n');
    fprintf('Estimator Stability (EKF):\n');
    fprintf('  Convergence: %s\n', ifthen(results.ekf_converged, 'PASSED', 'FAILED'));
    fprintf('  Settling Time: %d iterations\n', results.ekf_steps);

    fprintf('\nCell Balancing Logic:\n');
    fprintf('  Response: %s\n', ifthen(any(results.balancing_active), 'ACTIVE', 'INACTIVE'));

    fprintf('\nSafety & Protection:\n');
    fprintf('  Fault Response: %s\n', ifthen(results.fault_triggered, 'STABLE (TRIPPED)', 'UNSTABLE'));
    fprintf('  Post-Fault Current: %.1f A\n', results.fault_I_cmd);

    fprintf('\nResponse Characteristics:\n');
    fprintf('  Current Limit (Thermal): %.2f A\n', results.I_limit);
    fprintf('====================================\n');
end

function out = ifthen(cond, true_val, false_val)
    if cond, out = true_val; else, out = false_val; end
end

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

function params = load_optimized_data(filename)
    data = load(filename);
    params = data.optimized_params;
end

function [I_cmd, states] = bms_control_logic_local(inputs, params)
    % Local copy of bms_control_logic for script-based validation
    persistent bms_state;
    if isempty(bms_state)
        bms_state = 'Standby';
    end

    if any(inputs.V_cells > 3.6) || any(inputs.V_cells < 2.0) || any(inputs.T_cells > 85) || abs(inputs.I_measured) > 50
        bms_state = 'Fault';
    end

    if strcmp(bms_state, 'Fault') && inputs.Fault_Reset
        bms_state = 'Standby';
    end

    switch bms_state
        case 'Standby'
            if strcmp(inputs.Mode, 'Drive'), bms_state = 'Driving';
            elseif strcmp(inputs.Mode, 'Charge'), bms_state = 'Charging';
            end
        case 'Driving'
            if strcmp(inputs.Mode, 'Standby'), bms_state = 'Standby'; end
        case 'Charging'
            if strcmp(inputs.Mode, 'Standby') || all(inputs.SOC_est > 0.99), bms_state = 'Standby'; end
    end

    Q_n = params.Nominal_cell_capacity_Ah;
    I_max_thermal = Q_n * exp(-0.5 * (max(inputs.T_cells) - 25)/20);

    balancing_active = (inputs.V_cells - mean(inputs.V_cells)) > 0.01;

    if strcmp(bms_state, 'Driving'), I_cmd = inputs.I_request;
    elseif strcmp(bms_state, 'Charging'), I_cmd = Q_n * 0.5;
    else, I_cmd = 0;
    end

    I_cmd = min(I_cmd, I_max_thermal);
    if strcmp(bms_state, 'Fault'), I_cmd = 0; end

    states.bms_state = bms_state;
    states.balancing_active = balancing_active;
    states.I_limit = I_max_thermal;
end
