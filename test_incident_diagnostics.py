#!/usr/bin/env python3
"""
ConfigSync Dashboard - Incident Diagnostics Test Script
Tests field-level diffing, severity classification, root-cause suggestions,
and incident/postmortem record creation. Runs offline against mocked
DynamoDB tables so it does not require real AWS credentials.
"""

from unittest.mock import MagicMock
import json

import app


def test_field_diff():
    """Test field-level diffing between two config snapshots"""
    print("Testing field-level diffing...")

    old_config = json.dumps({
        'instance_type': 't3.micro',
        'state': 'running',
        'security_groups': ['sg-1']
    }, sort_keys=True)

    new_config = json.dumps({
        'instance_type': 't3.large',
        'state': 'running',
        'security_groups': ['sg-1', 'sg-open-all']
    }, sort_keys=True)

    diff = app.compute_field_diff(old_config, new_config)
    changed_fields = {entry['field'] for entry in diff}

    assert 'instance_type' in changed_fields, "instance_type change was not detected"
    assert 'security_groups' in changed_fields, "security_groups change was not detected"
    assert 'state' not in changed_fields, "unchanged field should not appear in the diff"

    print(f"✓ Field diff detected {len(diff)} changed field(s) correctly")


def test_severity_classification():
    """Test severity classification across drift types"""
    print("Testing severity classification...")

    security_group_drift = {
        'type': 'field_change',
        'field_diff': [{'field': 'security_groups', 'old_value': ['sg-1'], 'new_value': ['sg-1', 'sg-2'], 'change': 'modified'}]
    }
    assert app.classify_drift_severity(security_group_drift) == 'CRITICAL'

    tag_drift = {
        'type': 'field_change',
        'field_diff': [{'field': 'name', 'old_value': 'old-name', 'new_value': 'new-name', 'change': 'modified'}]
    }
    assert app.classify_drift_severity(tag_drift) == 'LOW'

    deleted_drift = {'type': 'deleted_resource'}
    assert app.classify_drift_severity(deleted_drift) == 'HIGH'

    parity_drift = {'type': 's3_parity'}
    assert app.classify_drift_severity(parity_drift) == 'HIGH'

    print("✓ Severity classification correctly ranks security, deletion, and cosmetic drifts")


def test_root_cause_suggestions():
    """Test that root cause and remediation suggestions are generated"""
    print("Testing root cause and remediation suggestions...")

    drift = {
        'type': 'field_change',
        'field_diff': [{'field': 'security_groups', 'old_value': ['sg-1'], 'new_value': ['sg-1', 'sg-2'], 'change': 'modified'}]
    }
    cause, action = app.suggest_root_cause_and_fix(drift)

    assert isinstance(cause, str) and len(cause) > 0, "likely_cause should be a non-empty string"
    assert isinstance(action, str) and len(action) > 0, "recommended_action should be a non-empty string"
    assert 'security group' in cause.lower()

    print("✓ Root cause and remediation suggestions generated correctly")


def test_enrich_drift_with_diagnostics():
    """Test that a drift dict is enriched with severity, cause, and action in place"""
    print("Testing drift enrichment...")

    drift = {
        'type': 'new_resource',
        'cloud': 'AWS',
        'resource_type': 'EC2',
        'resource_id': 'i-999',
        'resource_name': 'unexpected-instance',
        'change_type': 'New resource created',
        'timestamp': '2026-01-01T00:00:00'
    }
    app.enrich_drift_with_diagnostics(drift)

    assert 'severity' in drift
    assert 'likely_cause' in drift
    assert 'recommended_action' in drift

    print("✓ Drift dict enriched with severity, likely_cause, and recommended_action")


def test_build_incident_record():
    """Test building a postmortem-style incident record from a drift summary"""
    print("Testing incident record construction...")

    field_change = {
        'type': 'field_change', 'cloud': 'AWS', 'resource_type': 'EC2',
        'resource_id': 'i-1', 'resource_name': 'web-1', 'change_type': 'Configuration modified',
        'timestamp': '2026-01-01T00:00:00',
        'field_diff': [{'field': 'security_groups', 'old_value': ['sg-1'], 'new_value': ['sg-1', 'sg-2'], 'change': 'modified'}]
    }
    app.enrich_drift_with_diagnostics(field_change)

    deleted = {
        'type': 'deleted_resource', 'cloud': 'AWS', 'resource_type': 'EC2',
        'resource_id': 'i-2', 'resource_name': 'web-2', 'change_type': 'Resource deleted',
        'timestamp': '2026-01-01T00:00:00'
    }
    app.enrich_drift_with_diagnostics(deleted)

    drift_summary = {
        'timestamp': '2026-01-01T00:00:00',
        'drifts_detected': [field_change, deleted],
        'total_drifts': 2,
        'clouds_checked': ['AWS'],
        's3_parity_drifts': [],
        'total_s3_parity_drifts': 0
    }

    incident = app.build_incident_record('test@configsync.com', drift_summary)

    assert incident['user_email'] == 'test@configsync.com'
    assert incident['total_drifts'] == 2
    assert incident['severity_breakdown']['CRITICAL'] == 1
    assert incident['severity_breakdown']['HIGH'] == 1
    assert 'incident_id' in incident and incident['incident_id']
    assert 'executive_summary' in incident and incident['executive_summary']

    print(f"✓ Incident record built correctly: {incident['executive_summary']}")

    return incident


def test_save_and_retrieve_incident():
    """Test saving and retrieving incidents against a mocked Incidents table"""
    print("Testing incident persistence (mocked DynamoDB)...")

    original_table = app.incidents_table
    app.incidents_table = MagicMock()

    try:
        incident = test_build_incident_record()

        saved = app.save_incident(incident)
        assert saved is True
        app.incidents_table.put_item.assert_called_once_with(Item=incident)

        app.incidents_table.query.return_value = {'Items': [incident]}
        history = app.get_incident_history('test@configsync.com')
        assert history == [incident]

        app.incidents_table.get_item.return_value = {'Item': incident}
        detail = app.get_incident_detail('test@configsync.com', incident['incident_id'])
        assert detail == incident

        print("✓ Incident save, history query, and detail lookup all work correctly")
    finally:
        app.incidents_table = original_table


def run_all_tests():
    print("Testing ConfigSync Dashboard Incident Diagnostics...")
    print("=" * 60)

    test_field_diff()
    test_severity_classification()
    test_root_cause_suggestions()
    test_enrich_drift_with_diagnostics()
    test_build_incident_record()
    test_save_and_retrieve_incident()

    print("=" * 60)
    print("✓ All incident diagnostics tests passed")


if __name__ == '__main__':
    run_all_tests()
