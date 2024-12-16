import pandas as pd


class SEMetrics:
    REQUIRED_COLUMNS = ['rate_ask_ex', 'rate_bid_ex', 'rate_ask_start', 'rate_bid_start', 'start_time',
                        'ex_time']

    def __init__(self, df: pd.DataFrame):
        self.validate_dataframe(df)
        self.df = df

    @staticmethod
    def validate_dataframe(df: pd.DataFrame):
        """Validate if the DataFrame has all the required columns."""
        missing_columns = set(SEMetrics.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            raise ValueError(f"The DataFrame is missing the following required columns: {', '.join(missing_columns)}")

    def average(self, column) -> float:
        return self.df[column].mean()

    def min_value(self, column) -> float:
        return self.df[column].min()

    def max_value(self, column) -> float:
        return self.df[column].max()

    def average_difference(self, col1, col2) -> float:
        return (self.df[col1] - self.df[col2]).mean()

    def min_difference(self, col1, col2) -> float:
        return (self.df[col1] - self.df[col2]).min()

    def max_difference(self, col1, col2) -> float:
        return (self.df[col1] - self.df[col2]).max()

    def average_buy(self) -> float:
        """lower is good"""
        return self.average('rate_ask_ex')

    def average_sell(self) -> float:
        """higher is good"""
        return self.average('rate_bid_ex')

    def average_buy_saved(self) -> float:
        """Positive is good"""
        return self.average_difference('rate_ask_start', 'rate_ask_ex')

    def average_sell_gained(self) -> float:
        """Positive is good"""
        return self.average_difference('rate_bid_ex', 'rate_bid_start')

    def average_saved(self) -> float:
        """Positive is good"""
        return (self.average_buy_saved() + self.average_sell_gained()) / 2

    def min_buy_saved(self) -> float:
        return self.min_difference('rate_ask_start', 'rate_ask_ex')

    def min_sell_gained(self) -> float:
        return self.min_difference('rate_bid_ex', 'rate_bid_start')

    def average_execution_spread(self) -> float:
        return self.average_difference('rate_ask_ex', 'rate_bid_ex')

    def average_start_spread(self) -> float:
        return self.average_difference('rate_ask_start', 'rate_bid_start')

    def spread_benefit(self) -> float:
        """Positive is good"""
        return self.average_start_spread() - self.average_execution_spread()

    def max_execution_spread(self) -> float:
        return self.max_difference('rate_ask_ex', 'rate_bid_ex')

    def average_wait(self) -> float:
        """in hours"""
        return self.average_difference('ex_time', 'start_time').total_seconds() / 3600

    def min_wait(self) -> float:
        """in hours"""
        return self.min_difference('ex_time', 'start_time').total_seconds() / 3600

    def max_wait(self) -> float:
        """in hours"""
        return self.max_difference('ex_time', 'start_time').total_seconds() / 3600


if __name__ == '__main__':
    # Example DataFrame with datetime
    data = {
        'rate_ask_ex': [100, 150, 200],
        'rate_bid_ex': [95, 145, 190],
        'rate_ask_start': [105, 155, 205],
        'rate_bid_start': [90, 140, 185],
        'start_time': pd.to_datetime(['2023-01-01 00:00', '2023-01-02 00:00', '2023-01-03 00:00']),
        'ex_time': pd.to_datetime(['2023-01-01 03:00', '2023-01-02 03:00', '2023-01-03 03:00'])
    }
    df = pd.DataFrame(data)
    metrics = SEMetrics(df)

    metric_results = {
        "Average Buy": metrics.average_buy(),
        "Average Sell": metrics.average_sell(),
        "Average Buy Saved": metrics.average_buy_saved(),
        "Average Sell Gained": metrics.average_sell_gained(),
        "Average Saved": metrics.average_saved(),
        "Min Buy Saved": metrics.min_buy_saved(),
        "Min Sell Gained": metrics.min_sell_gained(),
        "Average Execution Spread": metrics.average_execution_spread(),
        "Average Start Spread": metrics.average_start_spread(),
        "Spread Benefit": metrics.spread_benefit(),
        "Max Execution Spread": metrics.max_execution_spread(),
        "Average Wait": metrics.average_wait(),
        "Min Wait": metrics.min_wait(),
        "Max Wait": metrics.max_wait()
    }
    for key, value in metric_results.items():
        print(f"{key}: {value}")
