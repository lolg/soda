import io

from juno.core.loaders.responses_loader import ResponsesLoader
from juno.core.schema import DataKey, importance_col, satisfaction_col


def test_load_jsonl():
    jsonl = """\
{"respondentId": 1, "outcomeId": 1, "importance": 3, "satisfaction": 3}
{"respondentId": 1, "outcomeId": 2, "importance": 4, "satisfaction": 4}
"""
    loader = ResponsesLoader(io.StringIO(jsonl))
    df = loader.load()

    # Should have 1 respondent row
    assert len(df) == 1
    assert df[DataKey.RESPONDENT_ID].iloc[0] == 1

    # Check wide columns exist and have correct values
    assert df[satisfaction_col(1)].iloc[0] == 3
    assert df[importance_col(1)].iloc[0] == 3
    assert df[satisfaction_col(2)].iloc[0] == 4
    assert df[importance_col(2)].iloc[0] == 4


def test_load_jsonl_two_respondents():
    jsonl = """\
{"respondentId": 1, "outcomeId": 1, "importance": 3, "satisfaction": 3}
{"respondentId": 1, "outcomeId": 2, "importance": 4, "satisfaction": 4}
{"respondentId": 2, "outcomeId": 1, "importance": 5, "satisfaction": 2}
{"respondentId": 2, "outcomeId": 2, "importance": 2, "satisfaction": 5}
"""
    loader = ResponsesLoader(io.StringIO(jsonl))
    df = loader.load()

    # Should have 2 respondent rows
    assert len(df) == 2
    assert set(df[DataKey.RESPONDENT_ID].values) == {1, 2}

    # Check respondent 1 values
    row1 = df[df[DataKey.RESPONDENT_ID] == 1].iloc[0]
    assert row1[satisfaction_col(1)] == 3
    assert row1[importance_col(1)] == 3
    assert row1[satisfaction_col(2)] == 4
    assert row1[importance_col(2)] == 4

    # Check respondent 2 values
    row2 = df[df[DataKey.RESPONDENT_ID] == 2].iloc[0]
    assert row2[satisfaction_col(1)] == 2
    assert row2[importance_col(1)] == 5
    assert row2[satisfaction_col(2)] == 5
    assert row2[importance_col(2)] == 2

