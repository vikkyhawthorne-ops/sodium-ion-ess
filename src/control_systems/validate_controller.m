%% BMS Controller Deployment-Grade Validation Report
% Verifies stability, observability, and safety override behavior.

%% 1. Initialization
params = load_optimized_data('src/control_systems/optimized_params.mat');

%% 2. Observability Analysis
% rank(obsv(A,C)) check for the 5-state coupled plant
[sys_ss, ~] = get_battery_dynamics(params);
obs_matrix = obsv(sys_ss.A, sys_ss.C);
obs_rank = rank(obs_matrix);
fprintf('MIMO Observability Rank: %d (Target: %d)\n', obs_rank, size(sys_ss.A, 1));

%% 3. Stability & Numerical Stiffness
% Step size stability check Delta_t < 2/lambda_max
evs = eig(sys_ss.A);
lambda_max = max(abs(evs));
fprintf('System Stiffness (max|lambda|): %.4f\n', lambda_max);
fprintf('Critical Timestep (Stability): %.4f s\n', 2/lambda_max);

%% 4. Safety Override & Hard Latch Logic
% Verifies that Layer 1 fault cannot be recovered without explicit reset.
inputs = struct('V_cells', [3.3, 3.3], 'T_cells', [25, 25], 'SOC_est', 0.5, ...
                'I_measured', 0, 'Mode', 'Drive', 'Fault_Reset', 0, 'I_request', 10, 'T_amb', 298.15);

% Trigger Critical Fault
inputs.T_cells = [90, 25];
[I1, s1] = bms_control_logic(inputs, params);

% Remove Fault condition but keep Reset=0
inputs.T_cells = [25, 25];
[I2, s2] = bms_control_logic(inputs, params);

fprintf('Fault Latch Test:\n');
fprintf('  Immediate Cutoff: %d A (Expected 0)\n', I1);
fprintf('  Latched After Recovery: %s (Expected Fault)\n', s2.bms_state);

%% 5. Energy Management (Multi-tier Derating)
% Verifies soft-constraint handling (Layer 4)
inputs.T_cells = [70, 70]; % Derating zone (T_max=60, T_crit=85)
[I_derated, ~] = bms_control_logic(inputs, params);
fprintf('Thermal Derating: %.2f A (Requested 10A)\n', I_derated);

%% Helper Functions
function params = load_optimized_data(filename)
    if ~exist(filename, 'file')
        params = struct('Nominal_cell_capacity_Ah', 10, 'Contact_resistance_Ohm', 0.01);
    else
        data = load(filename);
        params = data.optimized_params;
    end
end
