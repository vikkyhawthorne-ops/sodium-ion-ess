%% BMS Simulation Runner
% Consumes optimized parameters and executes control logic.
try
    params = load_optimized_data('src/control_systems/optimized_params.mat');
    % Dummy states for demonstration
    SOC = 0.8; V_t = 3.1; T = 25; SOH = 1.0; Grid_Stress = 0.1;
    [I_cmd] = bms_control_logic(SOC, V_t, T, SOH, Grid_Stress, params);
    fprintf('BMS command computed: %.2f A\n', I_cmd);

    results.max_temp = T;
    results.total_energy = 31.0; % kWh example
    generate_report(results);
catch ME
    fprintf('Error in BMS simulation: %s\n', ME.message);
end
