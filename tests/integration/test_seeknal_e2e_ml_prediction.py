"""
End-to-End Test: Kai Seeknal Agent - Feature Engineering with ML Prediction

This test demonstrates a complete data science workflow using Kai Seeknal Agent:
1. Load telecommunications customer activity data
2. Perform second-order aggregation for feature engineering
3. Train a machine learning model
4. Make predictions on a dummy label (customer churn indicator)

Dataset: /Users/fitrakacamarga/project/mta/signal/src/tests/data/feateng_comm_day/
- 73,194 rows × 35 columns
- Features: communication counts, durations, ratios
- Entity: msisdn (customer ID)
- Event time: day
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Add Seeknal to path
SEEKNAL_PATH = Path.home() / "project" / "mta" / "signal"
sys.path.insert(0, str(SEEKNAL_PATH / "src"))

# Add kai-code to path
KAI_CODE_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(KAI_CODE_PATH / "src"))

from kai_code.agents.seeknal import SeeknalAgent


class SeeknalE2ETest:
    """End-to-end test for Seeknal Agent with ML prediction."""

    def __init__(self, root_dir: Path):
        """Initialize the test.

        Args:
            root_dir: Root directory for the test
        """
        self.root_dir = root_dir
        self.data_path = (
            SEEKNAL_PATH / "src" / "tests" / "data" / "feateng_comm_day" /
            "part-00000-6ac5341d-c82b-4f80-8e7e-5cf8cae2aaac-c000.snappy.parquet"
        )
        self.agent = None
        self.project_name = "churn_prediction_e2e"
        self.entity_name = "customer"
        self.feature_group_name = "customer_activity_features"

    def setup(self):
        """Setup the test environment."""
        print("\n" + "="*80)
        print("SETUP: Initializing Kai Seeknal Agent")
        print("="*80)

        # Create agent
        self.agent = SeeknalAgent(
            root_dir=self.root_dir,
            seeknal_path=SEEKNAL_PATH,
            yolo=True,  # Auto-approve for testing
        )

        print(f"✓ Agent initialized")
        print(f"✓ Data path: {self.data_path}")
        print(f"✓ Project: {self.project_name}")
        return self

    def load_and_explore_data(self):
        """Step 1: Load and explore the dataset."""
        print("\n" + "="*80)
        print("STEP 1: Loading and Exploring Dataset")
        print("="*80)

        # Load data
        df = pd.read_parquet(self.data_path)

        print(f"\n✓ Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]} columns")
        print(f"\nColumn preview:")
        print(df.columns.tolist()[:10], "...")

        # Basic statistics
        print(f"\n✓ Date range: {df['day'].min()} to {df['day'].max()}")
        print(f"✓ Unique customers: {df['msisdn'].nunique():,}")
        print(f"✓ Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

        # Display sample data
        print(f"\n✓ Sample data:")
        print(df[['msisdn', 'day', 'comm_count_call_in', 'comm_count_call_out',
                  'comm_duration_call_in', 'comm_duration_call_out']].head(3))

        return df

    def create_dummy_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create a dummy churn label for ML prediction.

        Args:
            df: Input dataframe

        Returns:
            Dataframe with churn_label column
        """
        print("\n" + "="*80)
        print("STEP 2: Creating Dummy Churn Label")
        print("="*80)

        # Create a deterministic dummy label based on features
        # High activity customers = less likely to churn
        df['total_comm'] = (
            df['comm_count_call_in'] + df['comm_count_call_out'] +
            df['comm_count_sms_in'] + df['comm_count_sms_out']
        )

        # Create churn label: 1 if low activity, 0 otherwise
        median_activity = df['total_comm'].median()
        df['churn_label'] = (df['total_comm'] < median_activity).astype(int)

        churn_rate = df['churn_label'].mean() * 100
        print(f"\n✓ Created dummy churn label")
        print(f"✓ Churn rate: {churn_rate:.2f}%")
        print(f"✓ Label distribution:")
        print(df['churn_label'].value_counts())

        return df

    def create_seeknal_project(self):
        """Step 3: Create Seeknal project using Kai agent."""
        print("\n" + "="*80)
        print("STEP 3: Creating Seeknal Project")
        print("="*80)

        prompt = f"""
        Create a new Seeknal project named '{self.project_name}'
        with description 'End-to-end customer churn prediction pipeline'
        """

        result = self.agent.run(prompt.strip())
        print(f"\n✓ {result.output}")

        return result

    def create_entity(self):
        """Step 4: Create entity using Kai agent."""
        print("\n" + "="*80)
        print("STEP 4: Creating Entity")
        print("="*80)

        prompt = f"""
        Create an entity named '{self.entity_name}' with join key 'msisdn'
        """

        result = self.agent.run(prompt.strip())
        print(f"\n✓ {result.output}")

        return result

    def perform_second_order_aggregation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 5: Perform second-order aggregation for feature engineering.

        This creates time-based features using different windows:
        - Recent activity (last 7 days)
        - Medium-term activity (8-30 days)
        - Long-term activity (31-90 days)

        Args:
            df: Input dataframe

        Returns:
            Aggregated features dataframe
        """
        print("\n" + "="*80)
        print("STEP 5: Second-Order Aggregation for Feature Engineering")
        print("="*80)

        # Convert day column to datetime
        df['day'] = pd.to_datetime(df['day'])
        df['days_ago'] = (df['day'].max() - df['day']).dt.days

        # Define time windows
        windows = {
            'recent': (0, 7),
            'medium': (8, 30),
            'long': (31, 90)
        }

        # Feature columns to aggregate
        agg_features = [
            'comm_count_call_in', 'comm_count_call_out',
            'comm_count_sms_in', 'comm_count_sms_out',
            'comm_duration_call_in', 'comm_duration_call_out'
        ]

        # Perform aggregation
        aggregated_dfs = []
        for window_name, (min_days, max_days) in windows.items():
            print(f"\n  Aggregating {window_name} window ({min_days}-{max_days} days)...")

            window_df = df[
                (df['days_ago'] >= min_days) &
                (df['days_ago'] <= max_days)
            ].copy()

            # Aggregate by customer
            agg_df = window_df.groupby('msisdn').agg({
                **{f'{feat}': ['sum', 'mean', 'count'] for feat in agg_features}
            }).reset_index()

            # Flatten column names
            agg_df.columns = [
                'msisdn'] + [
                    f'{feat}_{agg}_{window_name}'
                    for feat in agg_features
                    for agg in ['sum', 'mean', 'count']
                ]

            aggregated_dfs.append(agg_df)
            print(f"    ✓ {window_name.capitalize()}: {len(agg_df):,} customers")

        # Merge all aggregations
        print(f"\n  Merging aggregated features...")
        final_df = aggregated_dfs[0]
        for agg_df in aggregated_dfs[1:]:
            final_df = final_df.merge(agg_df, on='msisdn', how='outer')

        # Fill NaN with 0
        final_df = final_df.fillna(0)

        print(f"\n✓ Second-order aggregation complete")
        print(f"✓ Final feature set: {final_df.shape[0]:,} customers × {final_df.shape[1]} features")

        # Display sample features
        print(f"\n✓ Sample aggregated features:")
        sample_cols = [col for col in final_df.columns if col != 'msisdn'][:5]
        print(final_df[['msisdn'] + sample_cols].head(3))

        return final_df

    def create_feature_group(self, aggregated_df: pd.DataFrame):
        """Step 6: Create feature group using Kai agent.

        Args:
            aggregated_df: Aggregated feature dataframe
        """
        print("\n" + "="*80)
        print("STEP 6: Creating Feature Group")
        print("="*80)

        # Save aggregated data for Seeknal
        output_path = self.root_dir / "aggregated_features.parquet"
        aggregated_df.to_parquet(output_path, index=False)
        print(f"\n✓ Saved aggregated features to: {output_path}")

        # Create feature group
        prompt = f"""
        Create a feature group named '{self.feature_group_name}'
        with entity '{self.entity_name}',
        using event_time_col 'aggregation_date',
        in project '{self.project_name}'

        The feature group contains:
        - Time-windowed communication features (recent, medium, long)
        - Aggregated counts and durations
        - Ready for ML model training
        """

        result = self.agent.run(prompt.strip())
        print(f"\n✓ {result.output}")

        return result, output_path

    def train_ml_model(self, df: pd.DataFrame):
        """Step 7: Train a simple ML model for churn prediction.

        Args:
            df: Feature dataframe with labels
        """
        print("\n" + "="*80)
        print("STEP 7: Training ML Model for Churn Prediction")
        print("="*80)

        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report, accuracy_score
        from sklearn.preprocessing import StandardScaler

        # Prepare features
        feature_cols = [col for col in df.columns if col not in ['msisdn', 'churn_label']]
        X = df[feature_cols].fillna(0)
        y = df['churn_label']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        print(f"\n✓ Training set: {len(X_train):,} samples")
        print(f"✓ Test set: {len(X_test):,} samples")

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        print(f"\n  Training Random Forest classifier...")
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        print(f"\n✓ Model training complete")
        print(f"✓ Test accuracy: {accuracy:.4f}")

        print(f"\n  Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['No Churn', 'Churn']))

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"\n  Top 10 Important Features:")
        print(feature_importance.head(10).to_string(index=False))

        return model, scaler, feature_importance

    def make_predictions(self, model, scaler, df: pd.DataFrame):
        """Step 8: Make predictions on new data.

        Args:
            model: Trained ML model
            scaler: Fitted scaler
            df: Feature dataframe
        """
        print("\n" + "="*80)
        print("STEP 8: Making Predictions")
        print("="*80)

        # Prepare features
        feature_cols = [col for col in df.columns if col not in ['msisdn', 'churn_label']]
        X = df[feature_cols].fillna(0)

        # Scale and predict
        X_scaled = scaler.transform(X)
        predictions = model.predict(X_scaled)
        probabilities = model.predict_proba(X_scaled)

        # Add predictions to dataframe
        df['predicted_churn'] = predictions
        df['churn_probability'] = probabilities[:, 1]

        # Summary
        print(f"\n✓ Predictions complete")
        print(f"✓ Predicted churn rate: {df['predicted_churn'].mean():.2%}")

        print(f"\n  Sample predictions:")
        sample = df[['msisdn', 'predicted_churn', 'churn_probability']].head(10)
        print(sample.to_string(index=False))

        # Distribution of probabilities
        print(f"\n  Churn probability distribution:")
        print(df['churn_probability'].describe())

        return df

    def cleanup(self):
        """Cleanup test resources."""
        print("\n" + "="*80)
        print("CLEANUP: Saving Session and Results")
        print("="*80)

        # Save agent session
        self.agent.save()
        print(f"\n✓ Agent session saved")

        print(f"\n✓ E2E Test Complete!")

    def run(self):
        """Run the complete end-to-end test."""
        try:
            # Setup
            self.setup()

            # Step 1: Load data
            df = self.load_and_explore_data()

            # Step 2: Create dummy label
            df = self.create_dummy_label(df)

            # Step 3: Create project
            self.create_seeknal_project()

            # Step 4: Create entity
            self.create_entity()

            # Step 5: Second-order aggregation
            aggregated_df = self.perform_second_order_aggregation(df)

            # Merge labels
            label_df = df[['msisdn', 'churn_label']].drop_duplicates()
            aggregated_df = aggregated_df.merge(label_df, on='msisdn', how='left')
            aggregated_df['churn_label'] = aggregated_df['churn_label'].fillna(0).astype(int)

            # Step 6: Create feature group
            self.create_feature_group(aggregated_df)

            # Step 7: Train ML model
            model, scaler, feature_importance = self.train_ml_model(aggregated_df)

            # Step 8: Make predictions
            predictions_df = self.make_predictions(model, scaler, aggregated_df)

            # Cleanup
            self.cleanup()

            return {
                'status': 'success',
                'dataset_shape': df.shape,
                'aggregated_shape': aggregated_df.shape,
                'churn_rate': df['churn_label'].mean(),
                'model_accuracy': 'computed',
                'predictions': predictions_df
            }

        except Exception as e:
            print(f"\n❌ Error during E2E test: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}


def main():
    """Run the E2E test."""
    # Create temp directory for test
    test_dir = Path.cwd() / "test_seeknal_e2e"
    test_dir.mkdir(exist_ok=True)

    print("\n" + "="*80)
    print("KAI SEEKNAL AGENT - E2E FEATURE ENGINEERING & ML PREDICTION TEST")
    print("="*80)
    print(f"\nTest Directory: {test_dir}")
    print(f"Seeknal Path: {SEEKNAL_PATH}")

    # Run test
    test = SeeknalE2ETest(test_dir)
    results = test.run()

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
