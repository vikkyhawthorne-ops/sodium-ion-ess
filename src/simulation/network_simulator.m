%% Multi-Feeder Network Simulator
% Ref: docs/paper.md section 3
% Models multi-feeder coupling via shared Solar-BESS sources.
% Tracks Network Realization State: XR = [dTheta_F1, dTheta_F2, ..., dTheta_Fn]

function results = network_simulator(num_feeders, load_profiles, p_solar, p_bess)
    % 1. Initialization
    if nargin < 1, num_feeders = 3; end
    if nargin < 2 || isempty(load_profiles)
        % Random RLC Load Profiles for n feeders
        load_profiles = cell(num_feeders, 1);
        for i = 1:num_feeders
            load_profiles{i} = [ones(24,1)*(30+rand()*20), ones(24,1)*(10+rand()*5), ones(24,1)*2];
        end
    end
    if nargin < 3, p_solar = 80; end % kW
    if nargin < 4, p_bess = 20; end  % kW

    results = struct();
    results.timestamp = datestr(now);
    results.shared_source.p_solar_kw = p_solar;
    results.shared_source.p_bess_kw = p_bess;
    results.shared_source.p_total_available = p_solar + p_bess;

    results.feeders = cell(num_feeders, 1);
    network_realization_state = zeros(num_feeders, 1);

    % 2. Power Balance Calculation
    total_p_load = 0;
    for i = 1:num_feeders
        total_p_load = total_p_load + mean(load_profiles{i}(:,1));
    end
    results.p_loss_est_kw = results.shared_source.p_total_available - total_p_load;

    % 3. Feeder-Level State Realization
    for f = 1:num_feeders
        feeder_id = ['Feeder_', num2str(f)];
        profile = load_profiles{f};

        P = profile(:,1);
        Q = profile(:,2);

        % Calculate Phase Dynamics (Realization State Component)
        % theta = atan(Q/P)
        theta_deg = atand(Q./P);

        % Relative Phase Deviation (Simulated relative to nominal 0.95 PF)
        nominal_theta = atand(sqrt(1-0.95^2)/0.95);
        delta_theta = theta_deg - nominal_theta;

        % 4. Result Aggregation
        results.feeders{f}.id = feeder_id;
        results.feeders{f}.p_kw = P;
        results.feeders{f}.q_kvar = Q;
        results.feeders{f}.theta_deg = theta_deg;
        results.feeders{f}.delta_theta = delta_theta;

        network_realization_state(f) = mean(delta_theta);

        % 5. Anomaly Detection Logic
        threshold = 5.0; % Degrees
        results.feeders{f}.anomaly_detected = any(abs(delta_theta) > threshold);
    end

    results.network_realization_state_xr = network_realization_state;
    results.global_anomaly = any(network_realization_state > 3.0); % Coupling threshold

    % 6. Export to JSON
    json_str = jsonencode(results);
    fid = fopen('network_realization.json', 'w');
    if fid ~= -1
        fprintf(fid, '%s', json_str);
        fclose(fid);
        disp('Multi-feeder network realization exported to network_realization.json');
    else
        warning('Could not open network_realization.json for writing.');
    end
end
