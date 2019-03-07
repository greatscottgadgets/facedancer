CC=$(TOOLCHAIN_PREFIX)gcc
CFLAGS+=-Wall
# CFLAGS+=-lcurl
OUT_LIB_DIR=lib
LIBNAME=kitty-agent
STATIC_LIB=$(OUT_LIB_DIR)/lib$(LIBNAME).a
JSON_DIR=json-c
STATIC_LIBS=$(JSON_DIR)/libjson-c.a
OBJ_DIR=obj
OBJ_FILES=$(OBJ_DIR)/kitty.o
SRC_DIR=.
HEADER_DIR=.
HEADER_FILES=$(HEADER_DIR)/kitty.h

all:directories $(STATIC_LIB)

.PHONY: directories

directories: $(OBJ_DIR) $(OUT_LIB_DIR)

$(OBJ_DIR) $(OUT_LIB_DIR):
	mkdir -p $@

$(STATIC_LIB):$(OBJ_FILES) $(STATIC_LIBS)
	ar -rcT $@ $^

$(OBJ_DIR)/%.o:$(SRC_DIR)/%.c $(HEADER_FILES)
	$(CC) $(CFLAGS) -I$(HEADER_DIR) -c -o $@ $<

clean:
	- rm -rf $(OBJ_DIR)
	- rm -rf $(OUT_LIB_DIR)
