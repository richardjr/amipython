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
# Extract just the single-precision float objects we need from libc.
# These only depend on mathieeesingbas.library (built into KS 3.1 ROM).
# Linking the full -lm would pull in mathieeedoubbas.library (not in ROM).
set(LIBC_A /opt/m68k-amigaos/m68k-amigaos/lib/libc.a)
set(FLOAT_OBJS
    lib_a-__addsf3.o lib_a-__subsf3.o lib_a-__mulsf3.o lib_a-__divsf3.o
    lib_a-__negsf2.o lib_a-__eqsf2.o lib_a-__fixsfsi.o lib_a-__floatsisf.o
)
set(FLOAT_DIR ${CMAKE_BINARY_DIR}/float_objs)
file(MAKE_DIRECTORY ${FLOAT_DIR})
foreach(OBJ ${FLOAT_OBJS})
    execute_process(
        COMMAND m68k-amigaos-ar x ${LIBC_A} ${OBJ}
        WORKING_DIRECTORY ${FLOAT_DIR}
    )
endforeach()
execute_process(
    COMMAND m68k-amigaos-ar rcs ${FLOAT_DIR}/libsfloat.a ${FLOAT_OBJS}
    WORKING_DIRECTORY ${FLOAT_DIR}
)
target_link_libraries(game ace ${FLOAT_DIR}/libsfloat.a)
target_compile_definitions(game PRIVATE AMIGA ACE_ENGINE)

# Output name without extension
if(GAME_OUTPUT_NAME)
    set_target_properties(game PROPERTIES OUTPUT_NAME "${GAME_OUTPUT_NAME}" SUFFIX "")
endif()
