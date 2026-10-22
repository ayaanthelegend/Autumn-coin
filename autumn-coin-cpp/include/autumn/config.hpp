#pragma once

#include "model.hpp"
#include "regime.hpp"
#include <string>
#include <vector>

namespace autumn {

bool load_base_config(const std::string& filepath,
                      FluidConfig& fluid,
                      CoeffsConfig& coeffs,
                      RegimeClassifierConfig& classifier);

std::vector<PlateConfig> load_coin_sets(const std::string& filepath);

std::vector<PlateConfig> load_coins_yaml(const std::string& filepath);

} // namespace autumn
