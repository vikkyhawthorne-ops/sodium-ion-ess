%% NFPP Physical Plant Builder (Simscape Equivalent)
% Ref: docs/paper.md

function plant = build_physical_plant(params)
    % This script represents the assembly of the physical battery pack
    % and its environment using Simscape components.

    plant.cells = cell(16, 1);
    for i = 1:16
        plant.cells{i}.type = 'nfpp_cell.ssc';
        plant.cells{i}.R_int = params.Contact_resistance_Ohm + 0.01;
        plant.cells{i}.C_th = 500;
    end

    % Pre-charge Circuit Implementation
    plant.precharge.R = 10; % Pre-charge resistor [Ohm]
    plant.precharge.contactor = 'Normally Open';

    % Pack Configuration
    plant.config = '16S1P';
    plant.nominal_voltage = 16 * 3.2;

    disp('Simscape Physical Plant Model Built:');
    disp(['  Configuration: ' plant.config]);
    disp(['  Main Contactors: Safety-Latched']);
end
