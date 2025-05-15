#include "json/json.h"
#include <string>
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <fstream>
#include <unistd.h>
#include <chrono>
#include <vector>
#include <numeric>
#include <cmath>

Json::Value read_cubes_json(const std::string& path)
{
    // open json and store it in a string
    std::ifstream infile(path + "cubes.json");
    std::stringstream instream;

    if ( infile.good() )
    {
        instream << infile.rdbuf();
        infile.close();
    }
    else
    {
        throw std::runtime_error("Failed reading the json file. Does the specified file exist?");
    }

    const std::string json_as_string = instream.str();


    // initialize json parser
    auto builder = new Json::CharReaderBuilder();
    auto reader = builder->newCharReader();

    Json::Value cubes_json;
    std::string errors;
    
    // parse json
    bool parsing_success = reader->parse(json_as_string.c_str(), json_as_string.c_str() + json_as_string.size(), &cubes_json, &errors);

    delete reader;
    delete builder;

    if (!parsing_success)
    {
        throw std::runtime_error("Failed parsing the json file: \n" + errors);
    }
    else
    {
        return cubes_json;
    }

}

void write_cubes_json(const Json::Value& cubes_json)
{
    std::string output_folder = cubes_json["output_folder"].asString();
    std::ofstream outfile(output_folder + "/cubes.json");
    outfile << cubes_json;
    outfile.close();
}

int main(int argc, char** argv)
{   
    // path to directory where cubes.json lies
    std::string json_path = argv[2];

    // read json file
    auto cubes_json = read_cubes_json(json_path);

    // info about task
    int n_cubes = cubes_json["n_cubes"].asInt();
    int n_processed = cubes_json["processed_cubes"].asInt();
    const std::string uuid = cubes_json["patient_uuid"].asString();
    const std::string patient_folder = cubes_json["output_folder"].asString();
    const std::string sim_folder = cubes_json["subdirs"][1].asString();
    const std::string out_folder = cubes_json["subdirs"][2].asString();

    // process specified amount of cubes
    int n_files = n_cubes - n_processed;
    if (argc == 4)  {
        int arg = std::stoi(argv[3]);
        if ( arg <= n_files ) 
        {
            n_files = arg;
        }
    }

    // print info
    std::cout << "Patient UUID: " << uuid << std::endl 
              << "Total amount of cubes: " << n_cubes << std::endl
              << "Already processed cubes: " << n_processed << std::endl
              << "Will run simulation on the next " << n_files << " cubes." << std::endl
              << "Start in 5 seconds... " << std::endl;
    sleep(5);

    // for time measurement
    std::vector<double> time_vector;
    time_vector.reserve(n_files);
    // main loop, call simulation once for every cube
    int file_count = 0;
    for (int i = n_processed; i < n_cubes && file_count < n_files; i++, file_count++)
    {   
        // input and output file names
        std::string g4dcm_filename = patient_folder + "/" + sim_folder + "/" + uuid + "_" + std::to_string(i) + ".g4dcm";
        std::string doseout_filename = patient_folder + "/" + out_folder + "/" + uuid + "_" + std::to_string(i) + ".out";
        
        // command to execute in cli

        // mpi command
        std::string mpi_command = "mpirun -np 20 --bind-to None --map-by hwthread  --report-bindings ";
        std::string command = mpi_command + "./DICOM_MPI " + (std::string)argv[1] + " " + g4dcm_filename + " " + doseout_filename;

        auto start_single = std::chrono::high_resolution_clock::now();

        // execute actual simulation
        auto success = system(command.c_str());

        auto stop_single = std::chrono::high_resolution_clock::now();

        // add run time to vector
        std::chrono::duration<double, std::milli> dur_ms = stop_single - start_single;
        time_vector.push_back(dur_ms.count());
    }


    // compute mean time and stddev 
    double sum = std::accumulate(time_vector.begin(), time_vector.end(), 0.);
    double mean = sum / time_vector.size();

    double sq_sum = std::inner_product(time_vector.begin(), time_vector.end(), time_vector.begin(), 0.);
    double stdev = std::sqrt(sq_sum / time_vector.size() - mean * mean);

    // print info
    std::cout << "Processed " << n_files << " file(s)." << std::endl
              << "Total time elapsed: Roughly " << sum/1000/60 << " minutes" << std::endl
              << "Time per simulation: " << mean/1000 << " +/- " << stdev/1000 << std::endl;
    
    // update the amount of processed cubes
    cubes_json["processed_cubes"] = n_processed + n_files;
    //cubes_json["processed_cubes"] = 0;

    // write json back to cubes.json file
    std::cout << "Writing cubes.json ...";
    write_cubes_json(cubes_json);
    std::cout << " Finished!" << std::endl;

    return 0;
}
