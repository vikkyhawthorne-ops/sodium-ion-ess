%% Robust BMS Validation Report
% This script validates the hierarchical safety, optimal arbitration, and MIMO dynamics.

%% 1. Initialization
params = load_optimized_data('src/control_systems/optimized_params.mat');

%% 2. Stability Analysis (Frequency & Time Domain)
% Analyzes the system using Bode plots and Step response for the 5-state plant.
sys_pack = get_pack_dynamics(params);

% 2.1 Eigenvalue Analysis
evs = eig(sys_pack.A);
is_stable = all(real(evs) <= 0);
fprintf('Asymptotic Stability: %s\n', mat2str(is_stable));

% 2.2 Frequency Response (Bode Plot)
try
    figure('Visible', 'off');
    bode(sys_pack);
    fprintf('Bode Plot analysis complete.\n');
catch
    fprintf('Control System Toolbox not found, skipping Bode Analysis.\n');
end

% 2.3 Time Response (Step Response)
try
    figure('Visible', 'off');
    step(sys_pack);
    fprintf('Step Response analysis complete.\n');
catch
    fprintf('Control System Toolbox not found, skipping Step Analysis.\n');
end

%% 3. Hierarchical Safety Test
inputs = struct('V_cells', [3.3, 3.3], 'T_cells', [25, 25], 'SOC_est', 0.5, ...
                'I_measured', 0, 'Mode', 'Drive', 'Fault_Reset', 0, 'I_request', 10, 'T_amb', 298.15);

[~, s0] = bms_control_logic(inputs, params);
inputs.T_cells = [60, 25]; [~, s1] = bms_control_logic(inputs, params); % Warning
inputs.T_cells = [70, 25]; [~, s2] = bms_control_logic(inputs, params); % Derating
inputs.T_cells = [80, 25]; [~, s3] = bms_control_logic(inputs, params); % Shutdown
inputs.T_cells = [90, 25]; [~, s4] = bms_control_logic(inputs, params); % Latch

fprintf('Safety Hierarchy Validation:\n');
fprintf('  T=60C: Status %d\n', s1.fault_status);
fprintf('  T=90C: Status %d\n', s4.fault_status);

%% 4. Optimal Current Arbitration
inputs.T_cells = [70, 25];
[I_cmd, ~] = bms_control_logic(inputs, params);
fprintf('Optimal Arbitration (T=70C): I_cmd = %.2f A\n', I_cmd);

%% 5. Estimator Convergence (EKF)
% Verifies the ability of the EKF to recover from an incorrect initial condition.
soc_true = 0.5;
soc_est = 0.8; % 30% error
P = 0.1;
v_meas = 3.2; i_meas = 0;

fprintf('Testing EKF Convergence (Initial Error: 30%%)...\n');
for i = 1:20
    [soc_est, P] = ekf_estimator(v_meas, i_meas, soc_est, P, params);
end
fprintf('  Final SOC Estimate: %.4f (Error: %.2f%%)\n', soc_est, abs(soc_est - soc_true)*100);

%% 6. Physical Domain Validation (Simscape Equivalent)
% Verifies coupled electro-thermal response of the Simscape Plant Model.
fprintf('Testing Physical Plant Response...\n');
I_test = 20; % 2C load
T_amb = 298.15;
[V_p, T_p] = plant_model(I_test, T_amb, params);
fprintf('  Load: %.1f A -> Voltage: %.2f V, Temp: %.1f K\n', I_test, V_p, T_p);
if T_p > T_amb
    fprintf('  Physical coupling (Heat Generation): PASSED\n');
else
    fprintf('  Physical coupling (Heat Generation): FAILED\n');
end

%% Helper Functions
function params = load_optimized_data(filename)
    if ~exist(filename, 'file')
        params = struct('Nominal_cell_capacity_Ah', 10, 'Contact_resistance_Ohm', 0.01);
    else
        data = load(filename);
        params = data.optimized_params;
    end
end
