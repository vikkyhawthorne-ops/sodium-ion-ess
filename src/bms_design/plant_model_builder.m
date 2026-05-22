%% NFPP Physical Plant Builder (Simscape Equivalent)
% Ref: docs/paper.md
% Updates: Chassis-Integrated Spreader with Fin System

function plant = build_physical_plant(params)
    % 1. Grid & Power Conditioning Layer
    plant.grid.type = 'grid_interface.ssc';
    plant.grid.estimators = {'RMS', 'Frequency', 'ROCOF', 'SRF-PLL'};

    plant.sts.type = 'static_transfer_switch.ssc';
    plant.pqc.type = 'power_quality_conditioner.ssc';

    % 2. Power Conversion Layer
    plant.pcs.type = 'bidirectional_dc_dc.ssc';

    % 3. Battery Pack & Chassis-Integrated Thermal Layer
    num_cells = 16;
    plant.cells = cell(num_cells, 1);
    for i = 1:num_cells
        cap_variation = 1 + (0.02 * randn());
        res_variation = 1 + (0.01 * randn());
        plant.cells{i}.type = 'nfpp_cell.ssc';
        plant.cells{i}.Q_nom = 10 * cap_variation;
        plant.cells{i}.R_0 = 0.01 * res_variation;

        % Integrated Spreader (touches cell and both chassis sides)
        plant.cells{i}.thermal.spreader.type = 'copper_spreader.ssc';
        plant.cells{i}.thermal.spreader.chassis_coupling = 'Dual-wall contact';
        plant.cells{i}.thermal.spreader.fins = 'High-density axial array';

        % Coolant coupling
        plant.cells{i}.thermal.tubing = 'coolant_tubing.ssc';
    end

    % 4. Active Cooling & Rejection Stage
    plant.cooling.pump = 'pump_actuator.ssc';
    plant.cooling.reject_port = 'reject_port_atomizer.ssc';
    plant.cooling.chassis_airflow = 'Finned spreader turbulent path';

    % 5. Interconnects & Sensors
    plant.busbar.resistance = 150e-6;
    plant.sensors.voltage.precision = '16-bit';

    % 6. Fault Injection Framework
    plant.faults = {
        'Voltage Sag', 'Frequency Instability', ...
        'Internal short', 'Cooling blockage', ...
        'Chassis heat soak'
    };

    plant.config = '16S1P';
    plant.nominal_voltage = 16 * 3.2;

    disp('ESS Digital Twin Model Built:');
    disp('  Chassis-Integrated Thermal Management with Finned Copper Spreader');
    disp('  Grid-Conditioned Power Electronics Layer Active');
end
