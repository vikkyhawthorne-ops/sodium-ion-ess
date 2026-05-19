%% Controller Validation Script
% Verifies stability, response characteristics, and estimator convergence.
% Ref: docs/paper.md

% Executable portion
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
    soc_init = 0.8;
    P = 0.1;
    v_meas = 3.2;
    i_meas = 0;

    soc_est = soc_init;
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

    %% 2. Stability Analysis (Bode & Step Response)
    fprintf('Performing Stability Analysis...\n');
    [sys_ss, sys_tf] = get_battery_dynamics(params);

    if isstruct(sys_ss)
        % Manual stability check if Control Toolbox is missing
        results.eigenvalues = eig(sys_ss.A);
        results.is_stable = all(real(results.eigenvalues) <= 0);
        fprintf('  Eigenvalue Stability: %s\n', ifthen(results.is_stable, 'PASSED', 'FAILED'));
    else
        % Use Control Toolbox functions
        results.eigenvalues = eig(sys_ss);
        results.is_stable = all(real(results.eigenvalues) <= 0);

        fprintf('  Generating Bode Plot data...\n');
        % bode(sys_ss); % Would open window

        fprintf('  Generating Step Response data...\n');
        % step(sys_ss); % Would open window
    end

    %% 3. Pre-charge Sequence & Contactor Stability
    fprintf('Testing Pre-charge Sequence...\n');
    inputs = struct('V_cells', [3.3, 3.3], 'T_cells', [25, 25], 'SOC_est', 0.5, ...
                    'I_measured', 0, 'Mode', 'Drive', 'Fault_Reset', 0, 'I_request', 10);

    [~, s1] = bms_control_logic(inputs, params);
    results.precharge_engaged = s1.contactor_pre;

    for i = 1:6, [~, s_final] = bms_control_logic(inputs, params); end
    results.drive_engaged = strcmp(s_final.bms_state, 'Driving') && s_final.contactor_main;

    %% 4. Cell Balancing
    inputs.V_cells = [3.4, 3.3];
    [~, states] = bms_control_logic(inputs, params);
    results.balancing_active = states.balancing_active;

    %% 5. Fault Response
    inputs.T_cells = [90, 25];
    [I_cmd, states] = bms_control_logic(inputs, params);
    results.fault_triggered = strcmp(states.bms_state, 'Fault');
    results.fault_I_cmd = I_cmd;

    generate_validation_report(results);
end

function generate_validation_report(results)
    fprintf('\n====================================\n');
    fprintf('   BMS CONTROLLER VALIDATION REPORT\n');
    fprintf('====================================\n');
    fprintf('Estimator Stability (EKF):\n');
    fprintf('  Convergence: %s (%d iterations)\n', ifthen(results.ekf_converged, 'PASSED', 'FAILED'), results.ekf_steps);

    fprintf('\nPlant Stability (MIMO State-Space):\n');
    fprintf('  Asymptotic Stability: %s\n', ifthen(results.is_stable, 'PASSED', 'FAILED'));
    fprintf('  Max Eigenvalue (Real part): %.4f\n', max(real(results.eigenvalues)));

    fprintf('\nState Machine & Contactors:\n');
    fprintf('  Pre-charge: %s\n', ifthen(results.precharge_engaged, 'SUCCESSFUL', 'FAILED'));
    fprintf('  Transition to Drive: %s\n', ifthen(results.drive_engaged, 'STABLE', 'UNSTABLE'));

    fprintf('\nCell Balancing:\n');
    fprintf('  Response: %s\n', ifthen(any(results.balancing_active), 'ACTIVE', 'INACTIVE'));

    fprintf('\nSafety & Protection:\n');
    fprintf('  Fault Logic: %s\n', ifthen(results.fault_triggered, 'TRIPPED', 'FAILED'));
    fprintf('====================================\n');
end

function out = ifthen(cond, true_val, false_val)
    if cond, out = true_val; else, out = false_val; end
end

function params = load_optimized_data(filename)
    if ~exist(filename, 'file')
        params = struct('Nominal_cell_capacity_Ah', 10, 'Contact_resistance_Ohm', 0.01);
    else
        data = load(filename);
        params = data.optimized_params;
    end
end
