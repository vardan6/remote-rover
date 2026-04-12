cmake_minimum_required(VERSION 3.8)
project(rover_sim_next)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  config
  launch
  rover_sim_next
  urdf
  worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
