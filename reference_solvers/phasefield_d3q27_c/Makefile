CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -pedantic

TARGET := phasefield_reference
SRC := phasefield_reference.cpp

.PHONY: all test clean

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

test: $(TARGET)
	./$(TARGET) --self-test

clean:
	rm -f $(TARGET) *.o selftest_diagnostics.csv math_validation_diagnostics.csv selftest_fields.vtk
