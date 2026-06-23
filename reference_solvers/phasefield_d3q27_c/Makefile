CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -pedantic

TARGET := phasefield_reference
SRC := phasefield_reference.cpp
MOMENTUM_TARGET := momentum_closure_single_node
MOMENTUM_SRC := momentum_closure_single_node.cpp

.PHONY: all test clean

all: $(TARGET) $(MOMENTUM_TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

$(MOMENTUM_TARGET): $(MOMENTUM_SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<

test: $(TARGET)
	./$(TARGET) --self-test

clean:
	rm -f $(TARGET) $(MOMENTUM_TARGET) *.o selftest_diagnostics.csv math_validation_diagnostics.csv selftest_fields.vtk
