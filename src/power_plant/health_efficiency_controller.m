%% PLANT HEALTH, EFFICIENCY, AND SURVIVABILITY CONTROLLER
% Ref: docs/paper.md section 2
% Focus: Residual-based fault detection and integrated efficiency maximization.

function [actions, states] = health_efficiency_controller(inputs, params)
    % inputs: struct {y_meas, x_dt, P_avail, price, Copex, time}
    %   y_meas: Measured variables [V, I, f, THD, Q]
    %   x_dt: Digital twin predictions for the same variables
    % params: struct {W_residual, safe_bounds, eta_target}

    persistent integral_efficiency;
    if isempty(integral_efficiency)
        integral_efficiency = 0;
    end

    %% 1. FAULT DETECTION (Digital Twin Residuals)
    % r(t) = y(t) - y_hat(t|x)
    residual = inputs.y_meas - inputs.x_dt;

    % Fault Indicator: F(t) = ||r(t)||_W
    F_t = sqrt(sum((residual .* params.W_residual).^2));

    fault_detected = F_t > params.safe_bounds.residual_threshold;

    %% 2. EFFICIENCY OPTIMIZATION
    % P_loss = P_inv + P_line + P_battery + P_thermal + P_harmonic
    P_loss = inputs.y_meas.P_loss;
    P_useful = inputs.y_meas.P_useful;

    eta_p = P_useful / (inputs.P_avail + 1e-6);
    integral_efficiency = integral_efficiency + eta_p;

    %% 3. MST OPERATING BOUNDARY LOGIC
    % Utilization U(t)
    U_t = P_useful + inputs.y_meas.P_battery_use;
    MST = inputs.Copex / (inputs.price + 1e-6);

    if (inputs.price * U_t) < inputs.Copex
        region = 'Unhealthy';
        % Action: Increase utilization/investigate faults
        dispatch_bias = 1.2;
    elseif U_t > params.safe_bounds.stress_limit
        region = 'Stress';
        % Action: Limit stress/protect asset
        dispatch_bias = 0.8;
    else
        region = 'Normal';
        dispatch_bias = 1.0;
    end

    %% 4. SURVIVABILITY ACTIONS
    if fault_detected
        actions.protection_mode = 'Active';
        actions.isolation_cmd = 1; % Trigger breakers if severe
    else
        actions.protection_mode = 'Monitoring';
        actions.isolation_cmd = 0;
    end

    actions.efficiency_bias = dispatch_bias;

    states.F_t = F_t;
    states.eta_plant = eta_p;
    states.region = region;
    states.fault_status = fault_detected;
    states.cum_efficiency = integral_efficiency;
end
