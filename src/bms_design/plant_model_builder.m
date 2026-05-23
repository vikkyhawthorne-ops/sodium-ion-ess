%% NFPP Physical Plant Builder (Simscape Equivalent)
% Ref: docs/paper.md
% Updates: 4-Pack Architecture, 4 Transverse Fin Sets, 45% Tube Contact

function plant = build_physical_plant(params)
    % 1. Grid & PCCS Subsystem
    plant.pccs.type = 'Power Conversion and Conditioning System';
    plant.pccs.topology = 'Grid -> STS -> PQC -> DC Link -> DC/DC';

    % 2. Modular Pack Assembly (16 Cells -> 4 Packs)
    num_packs = 4;
    cells_per_pack = 4;
    plant.packs = cell(num_packs, 1);

    for p = 1:num_packs
        plant.packs{p}.id = ['Pack_' num2str(p)];
        plant.packs{p}.cells = cell(cells_per_pack, 1);

        for c = 1:cells_per_pack
            plant.packs{p}.cells{c}.type = 'nfpp_cell.ssc';
            plant.packs{p}.cells{c}.casing = 'Poly-material only';
            plant.packs{p}.cells{c}.dims = [130, 70]; % mm
        end

        % Finned Tubing Interface (One set per pack boundary/interface)
        plant.packs{p}.thermal.fin_set.type = 'coolant_tubing.ssc';
        plant.packs{p}.thermal.fin_set.fins = 'Transverse (4 sets total)';
        plant.packs{p}.thermal.fin_set.contact = '45% Area-to-Tube';
    end

    % 3. ESS Unit Physical Dimensions (450x180x140 mm)
    plant.enclosure.type = 'aluminum_heat_sink.ssc';
    plant.enclosure.height = 450;
    plant.enclosure.length = 180;
    plant.enclosure.width = 140;

    % 4. Active Rejection System
    plant.cooling.atomizers = 2;
    plant.cooling.draft = '3-Airway (Left/Right Inlets, Back Outlet)';

    disp('Full ESS Digital Twin Built:');
    disp('  Hierarchy: 16S1P -> 4 Packs of 4 Cells');
    disp('  Thermal: 4 Transverse Fin Sets with 45% Tubing Contact');
    disp('  Chassis: Aluminum Heat Sink (450x180x140 mm)');
end
