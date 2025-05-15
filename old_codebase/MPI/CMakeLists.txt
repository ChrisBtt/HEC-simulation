#----------------------------------------------------------------------------
# Setup the project
cmake_minimum_required(VERSION 3.10 FATAL_ERROR)
project(DICOM_MPI)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -Wall -Wextra -Wpedantic")
set(CMAKE_CXX_FLAGS_DEBUG "-Wall -Wextra -Wpedantic")
set(CMAKE_CXX_COMPILER mpic++) 
set(G4mpi_DIR /home/dev/geant4/g4mpi-install/lib/G4mpi-10.7.0)

#----------------------------------------------------------------------------
# Find Geant4 package, activating all available UI and Vis drivers by default
# You can set WITH_GEANT4_UIVIS to OFF via the command line or ccmake/cmake-gui
# to build a batch mode only executable
#
option(WITH_GEANT4_UIVIS "Build example with Geant4 UI and Vis drivers" ON)
if(WITH_GEANT4_UIVIS)
  find_package(Geant4 REQUIRED ui_all vis_all)
else()
  find_package(Geant4 REQUIRED)
endif()

find_package(G4mpi REQUIRED)
#----------------------------------------------------------------------------
# Setup Geant4 include directories and compile definitions
#
include(${Geant4_USE_FILE})

#----------------------------------------------------------------------------
# Locate sources and headers for this project
#
include_directories(${PROJECT_SOURCE_DIR}/include
                    ${Geant4_INCLUDE_DIR}
                    ${G4mpi_INCLUDE_DIR})
file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.c*)
file(GLOB headers ${PROJECT_SOURCE_DIR}/include/*.h*)

#----------------------------------------------------------------------------
# Add the executable, and link it to the Geant4 libraries
#
add_executable(DICOM_MPI DICOM_MPI.cc ${sources} ${headers})
add_executable(simulations simulations.cc src/jsoncpp.cpp include/json/json.h)
target_link_libraries(DICOM_MPI ${Geant4_LIBRARIES} ${G4mpi_LIBRARIES})

#---------------------------------------------------------------------------
# Setup PSF compile Definitions
add_compile_options(
  PSF_READ
  PSF_WRITE
)

# Leaving both lines commented, the vanilla simulation is executed
# uncomment this line to enable reading from a phase space file
#target_compile_definitions(DICOM_MPI PUBLIC PSF_READ)
# uncomment this line to enable writing to a phase space file
#target_compile_definitions(DICOM_MPI PUBLIC PSF_WRITE)

#----------------------------------------------------------------------------
# Copy all scripts to the build directory, i.e. the directory in which we
# build DICOM. This is so that we can run the executable directly because it
# relies on these scripts being in the current working directory.
#
set(DICOM_SCRIPTS
    run.mac vis.mac ColourMap.dat CT2Density.dat)

foreach(_script ${DICOM_SCRIPTS})
  configure_file(
    ${PROJECT_SOURCE_DIR}/${_script}
    ${PROJECT_BINARY_DIR}/${_script}
    COPYONLY
    )
endforeach()

#add_custom_target(output ALL COMMAND ${CMAKE_COMMAND} -E make_directory $<TARGET_FILE_DIR:${PROJECT_NAME}>/output)

#add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
 #                  COMMAND ${CMAKE_COMMAND} -E copy_directory
  #                  ${CMAKE_SOURCE_DIR}/files $<TARGET_FILE_DIR:${PROJECT_NAME}>/files)
