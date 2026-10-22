#pragma once

#include "config.hpp"
#include <string>

namespace sph {

struct TestReport {
    int test_number = 0;
    std::string test_name;
    bool passed = false;
    std::string summary_metrics;
    std::string csv_path;
};

TestReport run_test_1();
TestReport run_test_2();
TestReport run_test_3();
TestReport run_test_4();
TestReport run_test_5();
TestReport run_test_6();
TestReport run_test_7();

void run_all_validation_tests();

} // namespace sph
