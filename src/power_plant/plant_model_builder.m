%% Physical Power Plant Builder
% Ref: docs/paper.md
% Updates: Standalone 16S1P pack and integrated power conversion digital twin.

function plant = build_physical_plant(params)
    % 0. Import Data from Pipeline (if available)
    data_file = 'final_validation.json';
    opt_params = struct();
    if exist(data_file, 'file')
        fid = fopen(data_file, 'r');
        raw = fread(fid, inf);
        str = char(raw');
        fclose(fid);
        data_decoded = jsondecode(str);
        if isfield(data_decoded, 'validation')
            opt_params = data_decoded.validation;
        end
    end

    % 1. Utility-Scale Interconnection & PCU
    plant.pccs.type = 'Utility-Scale Power Conditioning & Interconnection';
    plant.pccs.pcu.type = 'central_inverter_pcu.ssc';
    plant.pccs.pcu.rating_kva = 150;
    plant.pccs.transformer.type = 'step_up_transformer.ssc';
    plant.pccs.transformer.ratio = '415V/11kV';
    plant.pccs.switchgear.type = 'mv_switchgear.ssc';

    % 2. Microgrid Generation Assets
    plant.generation.solar.model = 'Mono-crystalline PV';
    plant.generation.solar.capacity_kwp = 100;
    plant.generation.primary_array.capacity_kw = 50;

    % 3. Modular AC-Coupled BESS Assembly (208 Modules)
    num_modules = 208;
    plant.bess.modules = cell(num_modules, 1);
    plant.bess.coupling = 'AC-Coupled via BESS-PCU';

    for m = 1:num_modules
        plant.bess.modules{m}.id = ['Module_' num2str(m)];
        plant.bess.modules{m}.type = 'nfpp_cell.ssc';
        plant.bess.modules{m}.interface = 'central_inverter_pcu.ssc';

        % Assign Pipeline-Informed Parameters
        if ~isempty(fieldnames(opt_params))
            plant.bess.modules{m}.R_0 = opt_params.R_0;
            plant.bess.modules{m}.V_nom = opt_params.V_nom;
            plant.bess.modules{m}.Q_nom = opt_params.capacity_ah;
        end
    end

    % 4. Enclosure & Environment
    plant.enclosure.type = 'Containerized Utility-Scale ESS';
    plant.enclosure.dims = [6058, 2438, 2591]; % mm (20ft ISO)

    disp('Full Hybrid Solar-Storage Power Plant Digital Twin Built:');
    disp(['  Generation: 100kWp Solar PV + 50kW Primary Array (Data source: ', data_file, ')']);
    disp('  BESS: 100kWh (208 Modular 16S1P Units)');
    disp('  Architecture: Utility-Scale (PCU, Step-up XFMR, MV Switchgear) ready.');
end
