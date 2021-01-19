import pytest

from great_expectations.checkpoint.checkpoint import (
    Checkpoint,
    CheckpointResult,
    SimpleCheckpointConfigurator,
)
from great_expectations.data_context.types.base import CheckpointConfig


@pytest.fixture
def update_data_docs_action():
    return {
        "name": "update_data_docs",
        "action": {"class_name": "UpdateDataDocsAction", "site_names": None},
    }


@pytest.fixture
def store_eval_parameter_action():
    return {
        "name": "store_evaluation_params",
        "action": {"class_name": "StoreEvaluationParametersAction"},
    }


@pytest.fixture
def store_validation_result_action():
    return {
        "name": "store_validation_result",
        "action": {"class_name": "StoreValidationResultAction"},
    }


@pytest.fixture
def webhook() -> str:
    return "https://hooks.slack.com/foo/bar"


@pytest.fixture
def slack_notification_action(webhook):
    return {
        "name": "send_slack_notification",
        "action": {
            "class_name": "SlackNotificationAction",
            "slack_webhook": webhook,
            "notify_on": "all",
            "notify_with": None,
            "renderer": {
                "module_name": "great_expectations.render.renderer.slack_renderer",
                "class_name": "SlackRenderer",
            },
        },
    }


@pytest.fixture
def context_with_data_source_and_empty_suite(
    titanic_pandas_data_context_with_v013_datasource_with_checkpoints_v1_with_empty_store,
):
    context = titanic_pandas_data_context_with_v013_datasource_with_checkpoints_v1_with_empty_store
    datasources = context.list_datasources()
    assert datasources[0]["class_name"] == "Datasource"
    assert "my_special_data_connector" in datasources[0]["data_connectors"].keys()
    context.create_expectation_suite("one", overwrite_existing=True)
    assert context.list_expectation_suite_names() == ["one"]
    return context


@pytest.fixture
def simple_checkpoint_defaults(context_with_data_source_and_empty_suite):
    return SimpleCheckpointConfigurator(
        "foo", context_with_data_source_and_empty_suite
    ).build()


@pytest.fixture
def two_validations(one_validation):
    return [
        one_validation,
        {
            "batch_request": {
                "datasource_name": "my_datasource",
                "data_connector_name": "my_special_data_connector",
                "data_asset_name": "users",
            },
            "expectation_suite_name": "two",
        },
    ]


def test_simple_checkpoint_default_properties_with_no_optional_arguments(
    empty_data_context,
    store_validation_result_action,
    store_eval_parameter_action,
    update_data_docs_action,
):
    """This demonstrates the simplest possible usage."""
    checkpoint = SimpleCheckpointConfigurator("foo", empty_data_context).build()
    assert isinstance(checkpoint, Checkpoint)

    assert checkpoint.name == "foo"
    assert checkpoint.data_context == empty_data_context
    assert checkpoint.action_list == [
        store_validation_result_action,
        store_eval_parameter_action,
        update_data_docs_action,
    ]
    assert checkpoint.config.config_version == 1.0
    assert checkpoint.config.class_name == "Checkpoint"
    assert checkpoint.config.evaluation_parameters == {}
    assert checkpoint.config.runtime_configuration == {}
    assert checkpoint.config.validations == []


def test_simple_checkpoint_raises_error_on_invalid_slack_webhook(
    empty_data_context,
):
    with pytest.raises(ValueError):
        SimpleCheckpointConfigurator(
            "foo", empty_data_context, slack_webhook="bad"
        ).build()


def test_simple_checkpoint_has_slack_action_with_defaults_when_slack_webhook_is_present(
    empty_data_context,
    store_validation_result_action,
    store_eval_parameter_action,
    update_data_docs_action,
    slack_notification_action,
    webhook,
):
    checkpoint = SimpleCheckpointConfigurator(
        "foo", empty_data_context, slack_webhook=webhook
    ).build()
    expected = [
        store_validation_result_action,
        store_eval_parameter_action,
        update_data_docs_action,
        slack_notification_action,
    ]
    assert checkpoint.action_list == expected
    assert checkpoint.config.action_list == [
        {
            "action": {"class_name": "StoreValidationResultAction"},
            "name": "store_validation_result",
        },
        {
            "action": {"class_name": "StoreEvaluationParametersAction"},
            "name": "store_evaluation_params",
        },
        {
            "action": {"class_name": "UpdateDataDocsAction", "site_names": None},
            "name": "update_data_docs",
        },
        {
            "name": "send_slack_notification",
            "action": {
                "class_name": "SlackNotificationAction",
                "notify_on": "all",
                "notify_with": None,
                "slack_webhook": "https://hooks.slack.com/foo/bar",
                "renderer": {
                    "module_name": "great_expectations.render.renderer.slack_renderer",
                    "class_name": "SlackRenderer",
                },
            },
        },
    ]


def test_simple_checkpoint_raises_error_on_invalid_notify_on(
    empty_data_context,
):
    for bad in [1, "bar", None, []]:
        with pytest.raises(ValueError):
            SimpleCheckpointConfigurator(
                "foo", empty_data_context, notify_on=bad
            ).build()


def test_simple_checkpoint_raises_error_on_missing_slack_webhook_when_notify_on_is_list(
    empty_data_context, slack_notification_action, webhook
):
    with pytest.raises(ValueError):
        SimpleCheckpointConfigurator(
            "foo", empty_data_context, notify_with=["prod", "dev"]
        ).build()


def test_simple_checkpoint_raises_error_on_missing_slack_webhook_when_notify_on_is_not_default(
    empty_data_context, slack_notification_action, webhook
):
    for condition in ["faliure", "success"]:
        with pytest.raises(ValueError):
            SimpleCheckpointConfigurator(
                "foo", empty_data_context, notify_on=condition
            ).build()


def test_simple_checkpoint_raises_error_on_invalid_notify_with(
    empty_data_context,
):
    for bad in [1, "bar", ["local_site", 3]]:
        with pytest.raises(ValueError):
            SimpleCheckpointConfigurator(
                "foo", empty_data_context, notify_with=bad
            ).build()


def test_simple_checkpoint_notify_with_all_has_data_docs_action_with_none_specified(
    empty_data_context, slack_notification_action, webhook
):
    """
    The underlying SlackNotificationAction and SlackRenderer default to
    including links to all sites if the key notify_with is not present. We are
    intentionally hiding this from users of SimpleCheckpoint by having a default
    of "all" that sets the configuration appropriately.
    """
    checkpoint = SimpleCheckpointConfigurator(
        "foo", empty_data_context, slack_webhook=webhook, notify_with="all"
    ).build()

    # set the config to include all sites
    slack_notification_action["action"]["notify_with"] = None
    assert slack_notification_action in checkpoint.action_list


def test_simple_checkpoint_has_slack_action_with_notify_adjustments_slack_webhook_is_present(
    empty_data_context,
    store_validation_result_action,
    store_eval_parameter_action,
    update_data_docs_action,
    slack_notification_action,
    webhook,
):
    checkpoint = SimpleCheckpointConfigurator(
        "foo",
        empty_data_context,
        slack_webhook=webhook,
        notify_on="failure",
        notify_with=["local_site", "s3_prod"],
    ).build()

    slack_notification_action["action"]["notify_on"] = "failure"
    slack_notification_action["action"]["notify_with"] = ["local_site", "s3_prod"]
    expected = [
        store_validation_result_action,
        store_eval_parameter_action,
        update_data_docs_action,
        slack_notification_action,
    ]
    assert checkpoint.action_list == expected


def test_simple_checkpoint_has_no_slack_action_when_no_slack_webhook_is_present(
    empty_data_context,
    store_validation_result_action,
    store_eval_parameter_action,
    update_data_docs_action,
):
    checkpoint = SimpleCheckpointConfigurator("foo", empty_data_context).build()
    assert checkpoint.action_list == [
        store_validation_result_action,
        store_eval_parameter_action,
        update_data_docs_action,
    ]


def test_simple_checkpoint_has_update_data_docs_action_that_should_update_all_sites_when_site_names_is_all(
    empty_data_context,
    store_validation_result_action,
    store_eval_parameter_action,
    update_data_docs_action,
):
    checkpoint = SimpleCheckpointConfigurator(
        "foo", empty_data_context, site_names="all"
    ).build()
    # This is confusing: the UpdateDataDocsAction default behavior is to update
    # all sites if site_names=None
    update_data_docs_action["action"]["site_names"] = None
    assert checkpoint.action_list == [
        store_validation_result_action,
        store_eval_parameter_action,
        update_data_docs_action,
    ]


def test_simple_checkpoint_raises_errors_on_invalid_site_name_types(
    empty_data_context,
):
    for junk_input in [[1, "local"], 1, ["local", None]]:
        with pytest.raises(TypeError):
            SimpleCheckpointConfigurator(
                "foo", empty_data_context, site_names=junk_input
            ).build()


def test_simple_checkpoint_raises_errors_on_site_name_that_does_not_exist_on_data_context(
    empty_data_context,
):
    # assert the fixture is adequate
    assert "prod" not in empty_data_context.get_site_names()
    with pytest.raises(ValueError):
        SimpleCheckpointConfigurator(
            "foo", empty_data_context, site_names=["prod"]
        ).build()


def test_simple_checkpoint_has_update_data_docs_action_that_should_update_selected_sites_when_sites_are_selected(
    empty_data_context,
    store_validation_result_action,
    store_eval_parameter_action,
    update_data_docs_action,
):
    # assert the fixture is adequate
    assert "local_site" in empty_data_context.get_site_names()

    checkpoint = SimpleCheckpointConfigurator(
        "foo", empty_data_context, site_names=["local_site"]
    ).build()
    # This is confusing: the UpdateDataDocsAction default behavior is to update
    # all sites if site_names=None
    update_data_docs_action["action"]["site_names"] = ["local_site"]
    assert checkpoint.action_list == [
        store_validation_result_action,
        store_eval_parameter_action,
        update_data_docs_action,
    ]


def test_simple_checkpoint_has_no_update_data_docs_action_when_site_names_is_none(
    empty_data_context,
    store_validation_result_action,
    store_eval_parameter_action,
    update_data_docs_action,
):
    # assert the fixture is adequate
    assert "local_site" in empty_data_context.get_site_names()

    checkpoint = SimpleCheckpointConfigurator(
        "foo", empty_data_context, site_names=None
    ).build()
    assert checkpoint.action_list == [
        store_validation_result_action,
        store_eval_parameter_action,
    ]


def test_simple_checkpoint_persisted_to_store(
    context_with_data_source_and_empty_suite, webhook, one_validation
):
    assert context_with_data_source_and_empty_suite.list_checkpoints() == []
    initial_checkpoint = SimpleCheckpointConfigurator(
        "foo",
        context_with_data_source_and_empty_suite,
        site_names=None,
    ).build()
    # TODO this add_checkpoint will be user facing and it could be more
    #  ergonomic by accepting a Checkpoint maybe .add_checkpoint() should take a
    #  Checkpoint and there should be a .create_checkpoint() that accepts all
    #  the current parameters
    context_with_data_source_and_empty_suite.add_checkpoint(
        **initial_checkpoint.config.to_json_dict()
    )
    assert context_with_data_source_and_empty_suite.list_checkpoints() == ["foo"]
    checkpoint = context_with_data_source_and_empty_suite.get_checkpoint("foo")
    assert isinstance(checkpoint, Checkpoint)
    assert isinstance(checkpoint.config, CheckpointConfig)
    assert checkpoint.config.to_json_dict() == {
        "action_list": [
            {
                "action": {"class_name": "StoreValidationResultAction"},
                "name": "store_validation_result",
            },
            {
                "action": {"class_name": "StoreEvaluationParametersAction"},
                "name": "store_evaluation_params",
            },
        ],
        "batch_request": None,
        "class_name": "Checkpoint",
        "config_version": 1.0,
        "evaluation_parameters": {},
        "expectation_suite_name": None,
        "module_name": "great_expectations.checkpoint",
        "name": "foo",
        "profilers": [],
        "run_name_template": None,
        "runtime_configuration": {},
        "template_name": None,
        "validations": [],
    }
    results = checkpoint.run(validations=[one_validation])
    assert results.success


def test_simple_checkpoint_defaults_run_and_no_run_params_returns_empty_checkpoint_result(
    context_with_data_source_and_empty_suite, simple_checkpoint_defaults
):
    result = simple_checkpoint_defaults.run()
    assert isinstance(result, CheckpointResult)
    assert result.success
    assert result.run_results == {}
    assert result.name == "foo"
    assert result.list_expectation_suite_names() == []


def test_simple_checkpoint_defaults_run_and_basic_run_params_without_persisting_checkpoint(
    context_with_data_source_and_empty_suite, simple_checkpoint_defaults, one_validation
):
    # verify checkpoint is not persisted in the data context
    assert context_with_data_source_and_empty_suite.list_checkpoints() == []
    result = simple_checkpoint_defaults.run(
        run_name="bar",
        validations=[one_validation],
    )
    assert isinstance(result, CheckpointResult)
    assert result.run_id.run_name == "bar"
    assert result.list_expectation_suite_names() == ["one"]
    assert len(result.list_validation_results()) == 1
    assert result.success


def test_simple_checkpoint_defaults_run_and_basic_run_params_with_persisted_checkpoint_loaded_from_store(
    context_with_data_source_and_empty_suite,
    simple_checkpoint_defaults,
    webhook,
    one_validation,
):
    context = context_with_data_source_and_empty_suite
    checkpoint = SimpleCheckpointConfigurator(
        "foo", context_with_data_source_and_empty_suite, slack_webhook=webhook
    ).build()
    context.add_checkpoint(**checkpoint.config.to_json_dict())
    checkpoint_name = checkpoint.name
    assert context.list_checkpoints() == [checkpoint_name]

    del checkpoint
    checkpoint = context.get_checkpoint(checkpoint_name)
    assert isinstance(checkpoint, Checkpoint)

    result = checkpoint.run(
        run_name="bar",
        validations=[one_validation],
    )
    assert isinstance(result, CheckpointResult)
    assert result.run_id.run_name == "bar"
    assert result.list_expectation_suite_names() == ["one"]
    assert len(result.list_validation_results()) == 1
    assert result.success


@pytest.fixture
def one_validation():
    return {
        "batch_request": {
            "datasource_name": "my_datasource",
            "data_connector_name": "my_special_data_connector",
            # TODO Alex why does a lack of data_asset_name working here?
            "data_asset_name": "users",
        },
        "expectation_suite_name": "one",
    }


def test_simple_checkpoint_defaults_run_with_top_level_batch_request_and_suite(
    context_with_data_source_and_empty_suite, simple_checkpoint_defaults
):
    result = simple_checkpoint_defaults.run(
        run_name="bar",
        batch_request={
            "datasource_name": "my_datasource",
            "data_connector_name": "my_special_data_connector",
            "data_asset_name": "users",
        },
        expectation_suite_name="one",
        validations=[{"expectation_suite_name": "one"}],
    )
    assert isinstance(result, CheckpointResult)
    assert result.success
    assert len(result.run_results) == 1


def test_simple_checkpoint_defaults_run_multiple_validations_without_persistence(
    context_with_data_source_and_empty_suite,
    simple_checkpoint_defaults,
    two_validations,
):
    context_with_data_source_and_empty_suite.create_expectation_suite("two")
    assert len(context_with_data_source_and_empty_suite.list_expectation_suites()) == 2
    result = simple_checkpoint_defaults.run(
        run_name="bar",
        validations=two_validations,
    )
    assert isinstance(result, CheckpointResult)
    assert result.run_id.run_name == "bar"
    assert sorted(result.list_expectation_suite_names()) == sorted(["one", "two"])
    assert len(result.list_validation_results()) == 2
    assert result.success


def test_simple_checkpoint_defaults_run_multiple_validations_with_persisted_checkpoint_loaded_from_store(
    context_with_data_source_and_empty_suite,
    simple_checkpoint_defaults,
    two_validations,
):
    context = context_with_data_source_and_empty_suite
    context.create_expectation_suite("two")
    assert len(context.list_expectation_suites()) == 2

    # persist to store
    context.add_checkpoint(**simple_checkpoint_defaults.config.to_json_dict())
    checkpoint_name = simple_checkpoint_defaults.name
    assert context.list_checkpoints() == [checkpoint_name]
    # reload from store
    del simple_checkpoint_defaults
    checkpoint = context.get_checkpoint(checkpoint_name)
    result = checkpoint.run(
        run_name="bar",
        validations=two_validations,
    )
    assert isinstance(result, CheckpointResult)
    assert result.run_id.run_name == "bar"
    assert sorted(result.list_expectation_suite_names()) == sorted(["one", "two"])
    assert len(result.list_validation_results()) == 2
    assert result.success