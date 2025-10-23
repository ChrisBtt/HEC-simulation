#----------------------------------------------------------------------------
# Setup the project
cmake_minimum_required(VERSION 3.16...3.27)
project(HEC-Simulation)

option(WITH_GEANT4_UIVIS "Build example with Geant4 UI and Vis drivers" ON)
if(WITH_GEANT4_UIVIS)
  find_package(Geant4 REQUIRED ui_all vis_all)
else()
  find_package(Geant4 REQUIRED)
endif()


#----------------------------------------------------------------------------
# Setup Geant4 include directories and compile definitions
#
include(${Geant4_USE_FILE})

#----------------------------------------------------------------------------
# Locate sources and headers for this project
#
include_directories(${PROJECT_SOURCE_DIR}/include
                    ${Geant4_INCLUDE_DIR})

file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cc)
file(GLOB headers ${PROJECT_SOURCE_DIR}/include/*.hh)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(DICOM DICOM.cc ${sources} ${headers})
target_link_libraries(DICOM ${Geant4_LIBRARIES})

add_executable(convertOutput convertOutput.cc)

#----------------------------------------------------------------------------
# Copy all scripts to the build directory, i.e. the directory in which we
# build DICOM. This is so that we can run the executable directly because it
# relies on these scripts being in the current working directory.
#

# the macros
set(DICOM_MACROS run.mac vis.mac)

# original set of DICOM data
set(DICOM_SCRIPTS
    ColourMap.dat CT2Density.dat
    Data.dat
)

# copy over scripts
foreach(_script ${DICOM_SCRIPTS})
    configure_file(
        ${PROJECT_SOURCE_DIR}/${_script}
        ${PROJECT_BINARY_DIR}/${_script}
        COPYONLY)
endforeach()

# copy over macros
foreach(_script ${DICOM_MACROS})
    configure_file(
        ${PROJECT_SOURCE_DIR}/${_script}
        ${PROJECT_BINARY_DIR}/${_script}
        COPYONLY)
endforeach()
