import pandas as pd

def simple_forecast(df):
    return df.groupby('time').size().rolling(3).mean()