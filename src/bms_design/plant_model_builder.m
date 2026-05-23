%% NFPP Physical Plant Builder (Simscape Equivalent)
% Ref: docs/paper.md
% Updates: Aluminum Heat Sink, 2 Atomizers, PCCS System

function plant = build_physical_plant(params)
    % 1. Grid & Power Conversion and Conditioning System (PCCS)
    plant.grid.type = 'grid_interface.ssc';
    plant.sts.type = 'static_transfer_switch.ssc';
    plant.pqc.type = 'power_quality_conditioner.ssc';
    plant.pcs.type = 'bidirectional_dc_dc.ssc';

    % 2. Battery Pack & Thermal Layer
    num_cells = 16;
    plant.cells = cell(num_cells, 1);
    for i = 1:num_cells
        cap_variation = 1 + (0.02 * randn());
        res_variation = 1 + (0.01 * randn());

        plant.cells{i}.type = 'nfpp_cell.ssc';
        plant.cells{i}.casing = 'Poly-material only';
        plant.cells{i}.Q_nom = 10 * cap_variation;

        % Thermal: Aluminum Heat Sink Enclosure
        plant.cells{i}.thermal.heatsink = 'aluminum_heat_sink.ssc';
        plant.cells{i}.thermal.tubing = 'coolant_tubing.ssc';
    end

    % 3. Cooling Infrastructure
    plant.cooling.pump = 'pump_actuator.ssc';
    plant.cooling.atomizers = '2 total (1 per side)';
    plant.cooling.topology = '3-Airway induced draft';

    % 4. Sensors & Diagnostics
    plant.sensors.voltage.precision = '16-bit';
    plant.diagnostics.manufacturing_optimization = 'Potential further gain through process refinements';

    plant.config = '16S1P';
    plant.nominal_voltage = 16 * 3.2;

    disp('ESS Digital Twin Model Built:');
    disp('  Thermal: Aluminum Heat Sink Enclosure + Sinusoidal Dual-Tube');
    disp('  Reject: Aerosol-Enhanced (2 Atomizers)');
    disp('  Power: Power Conversion and Conditioning System (PCCS)');
end
