%% NFPP Physical Plant Builder (Simscape Equivalent)
% Ref: docs/paper.md
% Updates: Full Multiphysics ESS Digital Twin (Grid-to-Cell) with Power Conditioning

function plant = build_physical_plant(params)
    % 1. Grid & Power Conditioning Layer
    plant.grid.type = 'grid_interface.ssc';
    plant.grid.estimators = {'RMS', 'Frequency', 'ROCOF', 'SRF-PLL'};

    plant.sts.type = 'static_transfer_switch.ssc';
    plant.sts.transfer_time = 4e-3; % 4ms

    plant.pqc.type = 'power_quality_conditioner.ssc';
    plant.pqc.logic = 'DVR-equivalent sag compensation';

    % 2. Power Conversion Layer
    plant.pcs.type = 'bidirectional_dc_dc.ssc';
    plant.pcs.efficiency = 0.96;

    % 3. Battery Pack Layer (16S1P)
    num_cells = 16;
    plant.cells = cell(num_cells, 1);
    for i = 1:num_cells
        cap_variation = 1 + (0.02 * randn());
        res_variation = 1 + (0.01 * randn());
        plant.cells{i}.type = 'nfpp_cell.ssc';
        plant.cells{i}.Q_nom = 10 * cap_variation;
        plant.cells{i}.R_0 = 0.01 * res_variation;
        plant.cells{i}.thermal.spreader = 'copper_spreader.ssc';
        plant.cells{i}.thermal.tubing = 'coolant_tubing.ssc';
    end

    % 4. Thermal Management Layer
    plant.cooling.pump = 'pump_actuator.ssc';
    plant.cooling.reject_port = 'reject_port_atomizer.ssc';
    plant.cooling.fin_system = 'Air-current guidance enclosure';

    % 5. Interconnects & Sensors
    plant.busbar.resistance = 150e-6;
    plant.sensors.voltage.precision = '16-bit';
    plant.sensors.current.type = 'Hall-effect bidirectional';

    % 6. Fault Injection Framework (Enhanced)
    plant.faults = {
        'Voltage Sag', ...
        'Frequency Instability', ...
        'STS Weld', ...
        'Internal short', ...
        'Converter efficiency drop', ...
        'Cooling blockage'
    };

    plant.config = '16S1P';
    plant.nominal_voltage = 16 * 3.2;

    disp('Full ESS Digital Twin Model Built:');
    disp('  Grid -> STS -> PQC -> DC Link -> DC/DC -> Pack');
    disp('  Features: Sag/Freq Compensation, Active Cooling, Stochastic Cells');
end
