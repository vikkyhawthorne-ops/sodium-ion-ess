%% SIMULINK BMS CONTROL SYSTEM MODEL
% Ref: docs/paper.md

function [I_cmd] = bms_control_logic(SOC, V_t, T, SOH, Grid_Stress, params)
    % params: Validated cell parameters struct (loaded from optimized_params.mat)

    Q_n = params.Nominal_cell_capacity_Ah;
    T_safe = 85; % Celsius
    lambda = 0.5;

    %% 3. C-RATE CONTROLLER
    C_ref = 1.0;
    I_ref = C_ref * Q_n;

    %% 5. THERMAL LIMITER
    if T > T_safe
        thermal_scaling = exp(-lambda * (T - T_safe));
    else
        thermal_scaling = 1.0;
    end

    if T > 85
        I_thermal = 0;
    else
        I_thermal = I_ref * thermal_scaling;
    end

    %% 6. GRID STRESS DERATING
    mu = 0.2;
    grid_scaling = exp(-mu * Grid_Stress);
    I_grid = I_ref * grid_scaling;

    %% Current Arbitration
    I_cmd = min([I_ref, I_thermal, I_grid]);

end

function params = load_optimized_data(filename)
    % Loads the .mat file exported by the validation pipeline
    data = load(filename);
    params = data.optimized_params;
    disp('Consuming Validated and Merged Cell Parameters:');
    disp(params);
end
