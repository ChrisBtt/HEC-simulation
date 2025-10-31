//
// Created by joshua on 7/8/25.
//
// This script takes the raw voxel data from the simulation, converts it into useful metrics and
// stores them in separate files for easy plotting

#include <fstream>
#include <iostream>
#include <string>
#include <map>
#include <sstream>
#include <array>
#include <vector>
#include <cmath>

int main(int argc, char** argv) {
    // Read input filename from command-line arguments
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <output file>" << std::endl;
        return 1;
    }
    std::string filename = argv[1];

    // Try to open input file
    std::ifstream fin(filename.c_str());
    if (!fin.is_open()) {
        std::cerr << "Error opening file: " << filename << std::endl;
        return 1;
    }

    // Read dose data first
    std::map<int, double> doses;
    std::string line;
    while (std::getline(fin, line)) {
        // Line "Cell Current X Y Z ZF ZB" denotes start of current data
        if (line.substr(0, 4) == "Cell") break;

        std::istringstream iss(line);
        int key;
        double value;
        if (iss >> key >> value) {
            if (key < 0) continue;
            doses[key] = value;
        }
    }

    // Read current data next
    std::map<int, std::array<double, 5>> currents;
    while (std::getline(fin, line)) {
        std::istringstream iss(line);
        int key;
        double x, y, z, zf, zb;
        if (iss >> key >> x >> y >> z >> zf >> zb) {
            if (key < 0) continue;
            currents[key] = {x, y, z, zf, zb};
        }
    }

    fin.close();

    // Store individual voxel measurements in separate files

    // Dose Depositions
    // Unit: Gy
    std::string dose_filename = filename + "_doses.txt";
    std::ofstream dose_out(dose_filename);
    dose_out << "Dose (Gy)\n";
    for (const auto &[index, dose]: doses) {
        dose_out << index << " " << dose << "\n";
    }
    dose_out.close();

    // Radial Currents
    // Unit: el / mm2
    std::string radial_filename = filename + "_radial_currents.txt";
    std::ofstream radial_out(radial_filename);
    radial_out << "Radial Current (el/mm2)\n";
    for (const auto &[index, current]: currents) {
        radial_out << index << " " << std::sqrt(current[0] * current[0] + current[1] * current[1]) << "\n";
    }
    radial_out.close();

    // Total XY-Currents
    // Unit: el / mm2
    std::string xy_filename = filename + "_xycurrents.txt";
    std::ofstream xy_out(xy_filename);
    xy_out << "XY-Current (el/mm2)\n";
    for (const auto &[index, current]: currents) {
        xy_out << index << " " << current[0] << " " << current[1] << "\n";
    }
    xy_out.close();

    // Total Z-Currents
    // Unit: el / mm2
    std::string z_filename = filename + "_zcurrents.txt";
    std::ofstream z_out(z_filename);
    z_out << "Z-Current (el/mm2)\n";
    for (const auto &[index, current]: currents) {
        z_out << index << " " << -current[2] << "\n";
    }
    z_out.close();

    // Forward Z-Currents
    // Unit: el / mm2
    std::string zf_filename = filename + "_zfcurrents.txt";
    std::ofstream zf_out(zf_filename);
    zf_out << "Z Current Forwards (el/mm2)\n";
    for (const auto &[index, current]: currents) {
        zf_out << index << " " << -current[3] << "\n";
    }
    zf_out.close();

    // Backward Z-Currents
    // Unit: el / mm2
    std::string zb_filename = filename + "_zbcurrents.txt";
    std::ofstream zb_out(zb_filename);
    zb_out << "Z Current Backwards (el/mm2)\n";
    for (const auto &[index, current]: currents) {
        zb_out << index << " " << current[4] << "\n";
    }
    zb_out.close();
}
