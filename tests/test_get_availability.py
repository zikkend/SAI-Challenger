import pytest
from saichallenger.common.sai_data import SaiObjType


@pytest.fixture(scope="module", autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip("invalid for \"{}\" testbed".format(testbed.name))

@pytest.fixture(autouse=True)
def on_prev_test_failure(prev_test_failed, npu):
    if prev_test_failed:
        npu.reset()


def _create_port_rif(npu, port_idx=0):
    npu.remove_vlan_member(npu.default_vlan_oid, npu.dot1q_bp_oids[port_idx])
    npu.remove(npu.dot1q_bp_oids[port_idx])
    return npu.create(
        SaiObjType.ROUTER_INTERFACE,
        [
            "SAI_ROUTER_INTERFACE_ATTR_TYPE", "SAI_ROUTER_INTERFACE_TYPE_PORT",
            "SAI_ROUTER_INTERFACE_ATTR_PORT_ID", npu.port_oids[port_idx],
            "SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID", npu.default_vrf_oid,
        ],
    )


def _restore_port_l2(npu, port_idx=0):
    bp_oid = npu.create(
        SaiObjType.BRIDGE_PORT,
        [
            "SAI_BRIDGE_PORT_ATTR_TYPE", "SAI_BRIDGE_PORT_TYPE_PORT",
            "SAI_BRIDGE_PORT_ATTR_PORT_ID", npu.port_oids[port_idx],
            "SAI_BRIDGE_PORT_ATTR_ADMIN_STATE", "true",
        ],
    )
    npu.dot1q_bp_oids[port_idx] = bp_oid
    npu.create_vlan_member(npu.default_vlan_oid, bp_oid, "SAI_VLAN_TAGGING_MODE_UNTAGGED")
    npu.set(npu.port_oids[port_idx], ["SAI_PORT_ATTR_PORT_VLAN_ID", npu.default_vlan_id])


def test_next_hop_get_availability(npu):
    """
    Description:
    Get next-hop object availability, create a next hop, and verify availability decreases.

    Test scenario:
    1. Get next-hop availability with no extra attributes
    2. Create a next-hop object
    3. Get availability again and verify it decreased
    4. Clean up configuration
    """
    nhop_ip = "10.10.10.10"
    dst_mac = "00:99:99:99:99:99"
    rif = _create_port_rif(npu)
    neighbor_key = npu._neighbor_entry_key(rif, nhop_ip)
    npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", dst_mac])
    nhop = None
    try:
        before = int(npu.get_availability("SAI_OBJECT_TYPE_NEXT_HOP:" + npu.switch_oid).value())
        nhop = npu.create(
            SaiObjType.NEXT_HOP,
            [
                "SAI_NEXT_HOP_ATTR_TYPE", "SAI_NEXT_HOP_TYPE_IP",
                "SAI_NEXT_HOP_ATTR_IP", nhop_ip,
                "SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID", rif,
            ],
        )
        after = int(npu.get_availability("SAI_OBJECT_TYPE_NEXT_HOP:" + npu.switch_oid).value())
        assert after == before - 1
    finally:
        if nhop:
            npu.remove(nhop)
        npu.remove(neighbor_key)
        npu.remove(rif)
        _restore_port_l2(npu)


def test_neighbor_get_availability(npu):
    """
    Description:
    Get neighbor entry availability, create a neighbor, and verify availability decreases.

    Test scenario:
    1. Get neighbor entry availability with no extra attributes
    2. Create a neighbor entry
    3. Get availability again and verify it decreased
    4. Clean up configuration
    """
    ipv4_addr = "10.10.10.1"
    mac_addr = "00:10:10:10:10:10"
    rif = _create_port_rif(npu)
    neighbor_key = npu._neighbor_entry_key(rif, ipv4_addr)
    try:
        before =  npu.get_availability(npu.switch_oid, ["OBJECT_TYPE","SAI_OBJECT_TYPE_NEIGHBOR_ENTRY"])
        print(before)
        npu.create(neighbor_key, ["SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS", mac_addr])
        after = int(npu.get_availability("SAI_OBJECT_TYPE_NEIGHBOR_ENTRY:" + npu.switch_oid).value())
        assert after == before - 1
    finally:
        npu.remove(neighbor_key)
        npu.remove(rif)
        _restore_port_l2(npu)
