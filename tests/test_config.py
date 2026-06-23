from src.config import Config


def test_config_instances_do_not_share_mutable_defaults():
    cfg_a = Config()
    cfg_b = Config()

    cfg_a.channel_dim["width"] = 999
    cfg_a.chip_layout["size_x"] = 999
    cfg_a.mixing_module["1to1"]["width"] = 999
    cfg_a.exclusion_zone_input.append({"name": "test_zone"})

    assert cfg_b.channel_dim["width"] == 150e-6
    assert cfg_b.chip_layout["size_x"] == 85.48e-3
    assert cfg_b.mixing_module["1to1"]["width"] == 10e-3
    assert cfg_b.exclusion_zone_input == []
