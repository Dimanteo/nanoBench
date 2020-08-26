LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)

LOCAL_MODULE := nb
LOCAL_SRC_FILES := ../nanoBench_main.c ../../common/nanoBench.c 
TARGET_ARCH_ABI := arm64-v8a
TARGET_PLATFORM := android-21

include $(BUILD_EXECUTABLE)