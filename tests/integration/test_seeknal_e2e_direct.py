"""
End-to-End Test: Seeknal Feature Engineering with ML Prediction

This test demonstrates a complete data science workflow using Seeknal library:
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


class SeeknalE2ETest:
    """End-to-end test for Seeknal with ML prediction."""

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
        self.project_name = "churn_prediction_e2e"
        self.entity_name = "customer"
        self.feature_group_name = "customer_activity_features"

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

    def perform_second_order_aggregation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 3: Perform second-order aggregation for feature engineering.

        This creates time-based features using different windows:
        - Recent activity (last 7 days)
        - Medium-term activity (8-30 days)
        - Long-term activity (31-90 days)

        This mimics Seeknal's SecondOrderAggregator behavior.

        Args:
            df: Input dataframe

        Returns:
            Aggregated features dataframe
        """
        print("\n" + "="*80)
        print("STEP 3: Second-Order Aggregation for Feature Engineering")
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

    def create_seeknal_project(self):
        """Step 4: Create Seeknal project."""
        print("\n" + "="*80)
        print("STEP 4: Creating Seeknal Project and Entity")
        print("="*80)

        try:
            from seeknal.project import Project
            from seeknal.entity import Entity

            # Create project
            project = Project(
                name=self.project_name,
                description="End-to-end customer churn prediction pipeline"
            )
            project.get_or_create()
            print(f"\n✓ Created project: {self.project_name}")

            # Create entity
            entity = Entity(name=self.entity_name, join_keys=["msisdn"])
            entity.get_or_create()
            print(f"✓ Created entity: {self.entity_name} with join_key: msisdn")

            return True
        except Exception as e:
            print(f"\n⚠ Warning: Could not create Seeknal project: {e}")
            print(f"   Continuing with feature engineering...")
            return False

    def train_ml_model(self, df: pd.DataFrame):
        """Step 5: Train a simple ML model for churn prediction.

        Args:
            df: Feature dataframe with labels
        """
        print("\n" + "="*80)
        print("STEP 5: Training ML Model for Churn Prediction")
        print("="*80)

        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
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

        print(f"\n  Confusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(f"  True Negatives: {cm[0][0]}")
        print(f"  False Positives: {cm[0][1]}")
        print(f"  False Negatives: {cm[1][0]}")
        print(f"  True Positives: {cm[1][1]}")

        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(f"\n  Top 10 Important Features:")
        print(feature_importance.head(10).to_string(index=False))

        return model, scaler, feature_importance

    def make_predictions(self, model, scaler, df: pd.DataFrame):
        """Step 6: Make predictions on new data.

        Args:
            model: Trained ML model
            scaler: Fitted scaler
            df: Feature dataframe
        """
        print("\n" + "="*80)
        print("STEP 6: Making Predictions")
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

        # High-risk customers (top 10%)
        high_risk_threshold = df['churn_probability'].quantile(0.9)
        high_risk_customers = df[df['churn_probability'] >= high_risk_threshold]
        print(f"\n  High-risk customers (top 10%): {len(high_risk_customers):,}")
        print(f"  Average churn probability: {high_risk_customers['churn_probability'].mean():.2%}")

        return df

    def save_results(self, df: pd.DataFrame, feature_importance: pd.DataFrame):
        """Step 7: Save results."""
        print("\n" + "="*80)
        print("STEP 7: Saving Results")
        print("="*80)

        # Save predictions
        output_path = self.root_dir / "predictions_with_churn.parquet"
        df.to_parquet(output_path, index=False)
        print(f"\n✓ Saved predictions to: {output_path}")

        # Save feature importance
        importance_path = self.root_dir / "feature_importance.csv"
        feature_importance.to_csv(importance_path, index=False)
        print(f"✓ Saved feature importance to: {importance_path}")

        # Create summary report
        summary = {
            'dataset_shape': df.shape,
            'total_customers': df['msisdn'].nunique(),
            'predicted_churn_rate': float(df['predicted_churn'].mean()),
            'avg_churn_probability': float(df['churn_probability'].mean()),
            'high_risk_customers': int(df[df['churn_probability'] >= 0.9].shape[0]),
            'timestamp': datetime.now().isoformat()
        }

        summary_path = self.root_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Saved summary to: {summary_path}")

        print(f"\n  Summary:")
        print(f"  - Total customers: {summary['total_customers']:,}")
        print(f"  - Predicted churn rate: {summary['predicted_churn_rate']:.2%}")
        print(f"  - High-risk customers: {summary['high_risk_customers']:,}")

    def run(self):
        """Run the complete end-to-end test."""
        try:
            print("\n" + "="*80)
            print("SEEKNAL E2E TEST: FEATURE ENGINEERING & ML PREDICTION")
            print("="*80)
            print(f"\nTest Directory: {self.root_dir}")
            print(f"Seeknal Path: {SEEKNAL_PATH}")

            # Step 1: Load data
            df = self.load_and_explore_data()

            # Step 2: Create dummy label
            df = self.create_dummy_label(df)

            # Step 3: Second-order aggregation
            aggregated_df = self.perform_second_order_aggregation(df)

            # Merge labels
            label_df = df[['msisdn', 'churn_label']].drop_duplicates()
            aggregated_df = aggregated_df.merge(label_df, on='msisdn', how='left')
            aggregated_df['churn_label'] = aggregated_df['churn_label'].fillna(0).astype(int)

            # Step 4: Create Seeknal project (optional)
            self.create_seeknal_project()

            # Step 5: Train ML model
            model, scaler, feature_importance = self.train_ml_model(aggregated_df)

            # Step 6: Make predictions
            predictions_df = self.make_predictions(model, scaler, aggregated_df)

            # Step 7: Save results
            self.save_results(predictions_df, feature_importance)

            print("\n" + "="*80)
            print("✓ E2E TEST COMPLETE!")
            print("="*80)

            return {
                'status': 'success',
                'dataset_shape': df.shape,
                'aggregated_shape': aggregated_df.shape,
                'churn_rate': float(df['churn_label'].mean()),
                'predicted_churn_rate': float(predictions_df['predicted_churn'].mean()),
            }

        except Exception as e:
            print(f"\n❌ Error during E2E test: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}


def main():
    """Run the E2E test."""
    # Create temp directory for test
    test_dir = Path.cwd() / "test_seeknal_e2e_results"
    test_dir.mkdir(exist_ok=True)

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
