cmake_minimum_required(VERSION 3.14)
project(amipython_game C)

# ACE_DIR must be set (points to ACE root with pre-built library)
if(NOT DEFINED ENV{ACE_DIR})
    message(FATAL_ERROR "ACE_DIR environment variable not set")
endif()

set(ACE_DIR $ENV{ACE_DIR})

# Add ACE — re-uses ACE's CMakeLists.txt which creates the 'ace' target.
# Since ACE is already built, CMake will find it's up-to-date and skip rebuild.
add_subdirectory(${ACE_DIR} ace)

# The game binary
add_executable(game game.c amipython_engine_amiga.c)
target_include_directories(game PRIVATE ${ACE_DIR}/include ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(game ace)
target_compile_definitions(game PRIVATE AMIGA ACE_ENGINE)

# Output name without extension
if(GAME_OUTPUT_NAME)
    set_target_properties(game PROPERTIES OUTPUT_NAME "${GAME_OUTPUT_NAME}" SUFFIX "")
endif()
