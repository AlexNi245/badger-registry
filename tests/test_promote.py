import brownie
from brownie import ZERO_ADDRESS, accounts


def test_vault_promotion(registry, vault, rando, gov):

    # Author adds vault to their list
    registry.add("v1", vault, "my-meta-data", {"from": rando})
    assert registry.getVaults("v1", rando) == [[vault], ["my-meta-data"]]

    # Random user attempts to promote vault and reverts
    with brownie.reverts():
        registry.promote("v1", vault, 0, {"from": rando})

    # Governance is able to promote vault
    tx = registry.promote("v1", vault, 0, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 0) == [[vault], ["my-meta-data"]]

    event = tx.events["PromoteVault"][0]
    assert event["vault"] == vault

    # Same vault cannot be promoted twice (nothing happens)
    tx = registry.promote("v1", vault, 0, {"from": gov})
    assert len(tx.events) == 0


def test_vault_promotion_step_staging(registry, vault, rando, gov):
    registry.promote("v1", vault, 0, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 0) == [[vault], [""]]

    registry.promote("v1", vault, 1, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 1) == [[vault], [""]]

    ## After promoting a vault to the next steps, it's no longer in the previous step
    assert registry.getFilteredProductionVaults("v1", 0) == [[], []]


def test_vault_promotion_step_prod(registry, vault, rando, gov):
    registry.promote("v1", vault, 0, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 0) == [[vault], [""]]

    registry.promote("v1", vault, 2, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 2) == [[vault], [""]]

    ## After promoting a vault to the next steps, it's no longer in the previous steps
    assert registry.getFilteredProductionVaults("v1", 0) == [[], []]


def test_vault_promotion_step_deprecated(registry, vault, rando, gov):
    registry.promote("v1", vault, 0, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 0) == [[vault], [""]]

    registry.promote("v1", vault, 2, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 2) == [[vault], [""]]

    ## Cant promote to deprecated
    with brownie.reverts():
        registry.promote("v1", vault, 3, {"from": gov})


def test_vault_promotion_order(registry, vault, vault_one, vault_two, gov):
    # Promotion can be only happen in one direction
    # If a user try to lower the status of a vault using the promote function the function should revert

    # Cant promote from open -> guarded
    registry.promote("v1", vault, 2, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 2) == [[vault], [""]]
    with brownie.reverts():
        registry.promote("v1", vault, 1, {"from": gov})

    # Cant promote from deprecated -> open
    registry.demote("v1", vault_one, 3, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 3) == [[vault_one], [""]]
    with brownie.reverts():
        registry.promote("v1", vault_one, 2, {"from": gov})

    # Cant promote from deprecated -> guarded
    registry.demote("v1", vault_two, 3, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 3) == [[vault_one,vault_two], ["",""]]
    with brownie.reverts():
        registry.promote("v1", vault_two, 1, {"from": gov})


def test_vault_promotion_permissions(
    registry, vault, vault_one, rando, gov, devGov, strategistGuild
):
    ## If devGov promotes, the only step is 0
    #
    # If gov promotes, it goes to any step
    # Rando can't promote

    with brownie.reverts():
        registry.promote("v1", vault, 2, {"from": rando})

    ## Even though we put 2 here, we still only go to 0 because devGov is limited to it
    registry.promote("v1", vault, 2, {"from": devGov})
    assert registry.getFilteredProductionVaults("v1", 0) == [[vault], [""]]
    assert registry.getFilteredProductionVaults("v1", 2) == [[], []]

    ## strategistGuild can promote to anything
    registry.promote("v1", vault, 2, {"from": strategistGuild})
    ## And promoting cleans up lower ranks
    assert registry.getFilteredProductionVaults("v1", 0) == [[], []]
    assert registry.getFilteredProductionVaults("v1", 2) == [[vault], [""]]

    ## Gov can promote to anything
    registry.promote("v1", vault_one, 2, {"from": gov})
    ## And promoting cleans up lower ranks
    assert registry.getFilteredProductionVaults("v1", 0) == [[], []]
    assert registry.getFilteredProductionVaults("v1", 2) == [
        [vault, vault_one],
        ["", ""],
    ]


def test_vault_promotion_version(registry, vault, rando, gov):
    #Can promote a supported version
    registry.promote("v1", vault, 2, {"from": gov})
    assert registry.getFilteredProductionVaults("v1", 2) == [[vault], [""]]

    ## Cant promote to deprecated
    with brownie.reverts():
        registry.promote("v10", vault, 2, {"from": gov})