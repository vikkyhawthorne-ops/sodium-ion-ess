%% Physical Power Plant Builder
% Ref: docs/paper.md
% Updates: Integrated Plant–Network Digital Twin for State Estimation

function plant = build_physical_plant(params)
    % 0. Import Data from Pipeline (Mandatory Dependency)
    script_dir = fileparts(mfilename('fullpath'));
    data_file = fullfile(script_dir, 'cell_params.json');

    if ~exist(data_file, 'file')
        error('Mandatory pipeline artifact missing: %s. Run simulation/envelope.py first.', data_file);
    end

    fid = fopen(data_file, 'r');
    raw = fread(fid, inf);
    str = char(raw');
    fclose(fid);
    data_decoded = jsondecode(str);

    if ~isfield(data_decoded, 'ssc_params')
        error('Invalid data structure in %s. Missing ssc_params.', data_file);
    end
    ssc_params = data_decoded.ssc_params;

    % 1. Utility-Scale 3-Phase Interconnection & PCU
    plant.pccs.type = 'Utility-Scale Balanced 3-Phase Interconnection';
    plant.pccs.pcu.type = 'central_inverter_pcu.ssc';
    plant.pccs.pcu.rating_kva = 150;
    plant.pccs.transformer.type = 'step_up_transformer.ssc';
    plant.pccs.transformer.ratio = '415V/11kV';
    plant.pccs.switchgear.type = 'mv_switchgear.ssc';

    % 2. Service Main & State Estimation Interface (PCC)
    plant.mains.model = 'service_main.ssc';
    plant.mains.state_vector = {'V', 'I', 'f', 'THD', 'Q'};

    % 3. Microgrid Generation Assets
    plant.generation.solar.capacity_kwp = 100;
    plant.generation.primary_array.capacity_kw = 50;

    % 4. Representation Loads & Nodal Monitoring
    plant.loads.model = 'utility_load.ssc';
    plant.loads.p_nom_kw = 50;
    plant.monitoring.feeders = 2;

    % 5. Modular AC-Coupled BESS Assembly (208 Modules / 100kWh)
    num_modules = 208;
    plant.bess.modules = cell(num_modules, 1);
    plant.bess.topology = '16S1P per Module (48V, 10Ah)';

    for m = 1:num_modules
        plant.bess.modules{m}.id = ['Module_' num2str(m)];
        plant.bess.modules{m}.type = 'nfpp_cell.ssc';

        % Assign DFN-Informed Parameters from Pipeline
        plant.bess.modules{m}.R_0 = ssc_params.R_0;
        plant.bess.modules{m}.V_nom = ssc_params.V_nom;
        plant.bess.modules{m}.Q_nom = ssc_params.Q_nom;
        plant.bess.modules{m}.R1 = ssc_params.R1;
        plant.bess.modules{m}.C1 = ssc_params.C1;
        plant.bess.modules{m}.R2 = ssc_params.R2;
        plant.bess.modules{m}.C2 = ssc_params.C2;
        plant.bess.modules{m}.C_th_core = ssc_params.C_th_core;
    end

    % 6. Enclosure & Environment
    plant.enclosure.type = '20ft ISO Containerized Utility-Scale ESS';
    plant.enclosure.dims_mm = [6058, 2438, 2591];

    disp('--- Plant-Network Digital Twin Initialization ---');
    disp(['  Source: ', data_file]);
    disp(['  Monitoring Interface: ', plant.mains.model, ' (PCC State Estimation)']);
    disp(['  Generation: 100kWp Solar + 50kW Primary']);
    disp(['  BESS: ', num2str(num_modules), ' Modular Units (100kWh Class)']);
    disp('  Status: Ready for State Estimation & Fault Detection Analysis.');
end
