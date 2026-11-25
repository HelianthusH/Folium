cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(voicecard VERSION 1.0)
target_sources(app PRIVATE src/main.c src/storage.c src/codec.c src/link.c src/rtc.c)

