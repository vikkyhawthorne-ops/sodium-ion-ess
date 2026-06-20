%% Network Simulator
% Ref: docs/paper.md section 3
% Attaches different topologies and RLC load profiles to 2 feeders.

function results = network_simulator(topologies, load_profiles)
    % 1. Initialization
    if nargin < 1
        topologies = {'Radial', 'Ring'};
    end
    if nargin < 2
        % RLC Load Profiles: P (kW), Q (kVAr), Harmonics (THD %)
        load_profiles = {
            [ones(24,1)*50, ones(24,1)*15, ones(24,1)*2]; % Feeder 1
            [ones(24,1)*30, ones(24,1)*10, ones(24,1)*5]  % Feeder 2
        };
    end

    results = struct();
    results.timestamp = datestr(now);
    results.feeders = cell(2, 1);

    % 2. Topology and RLC Load Attachment Loop
    for f = 1:2
        feeder_id = ['Feeder_', num2str(f)];
        topology = topologies{mod(f-1, length(topologies)) + 1};
        profile = load_profiles{f};

        P = profile(:,1);
        Q = profile(:,2);
        THD = profile(:,3);

        % 3. Phase Change Measurements
        % Calculate Phase Shift from P and Q (theta = atan(Q/P))
        phase_shift_deg = atand(Q./P);
        pf = cosd(phase_shift_deg);

        voltage_phase = [0, -120, 120]; % Balanced 3-Phase
        current_phase = repmat(voltage_phase, length(pf), 1) - repmat(phase_shift_deg, 1, 3);

        % 4. Result Aggregation
        results.feeders{f}.id = feeder_id;
        results.feeders{f}.topology = topology;
        results.feeders{f}.rlc_profile.p_kw = P;
        results.feeders{f}.rlc_profile.q_kvar = Q;
        results.feeders{f}.rlc_profile.thd_percent = THD;
        results.feeders{f}.measurements.power_factor = pf;
        results.feeders{f}.measurements.phase_shift_deg = phase_shift_deg;
        results.feeders{f}.measurements.voltage_phases = voltage_phase;
        results.feeders{f}.measurements.current_phases = current_phase;
    end

    % 5. Export to JSON
    json_str = jsonencode(results);
    fid = fopen('network_results.json', 'w');
    if fid ~= -1
        fprintf(fid, '%s', json_str);
        fclose(fid);
        disp('Network simulation results (RLC) exported to network_results.json');
    else
        warning('Could not open network_results.json for writing.');
    end
end
