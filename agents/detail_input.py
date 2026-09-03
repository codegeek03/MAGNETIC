import asyncio
import json
import logging
import os
from typing import Dict, Optional, Union

from libs.shared.settings import get_settings

_settings = get_settings()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

JsonData = Dict[str, Union[str, int, float, Dict[str, float], Dict[str, str]]]

class ProductInput:
    def __init__(self, current_time: str = None, user_login: str = None):
        self.product_name = ""
        self.units_per_shipment = 0
        self.dimensions = {"length": 0, "width": 0, "height": 0}
        self.packaging_location = ""
        self.budget_constraint = 0.0
        # Default weights come from settings; the UI flow can override them
        self.analysis_weights = _settings.analysis_weights.as_dict()
        # Use live settings values if caller doesn't supply overrides
        self.timestamp = current_time or _settings.now_utc()
        self.user = user_login or _settings.current_user

    async def validate_product_details(self) -> Optional[str]:
        if not self.product_name:
            return "Product name cannot be empty"
        if self.units_per_shipment <= 0:
            return "Units per shipment must be positive"
        if any(dim <= 0 for dim in self.dimensions.values()):
            return "All dimensions must be positive"
        if not self.packaging_location:
            return "Packaging location cannot be empty"
        if self.budget_constraint <= 0:
            return "Budget constraint must be positive"
        if abs(sum(self.analysis_weights.values()) - 1.0) > 0.01:
            return "Analysis weights must sum to 1.0"
        return None

    async def get_analysis_weights(self) -> None:
        print("\nEnter Analysis Weights (they must sum to 1.0):")
        keys = list(self.analysis_weights.keys())
        new_weights = {}
        total = 0.0
        for key in keys:
            while True:
                try:
                    value = float(input(f"{key.capitalize()} weight: "))
                    if 0 <= value <= 1:
                        new_weights[key] = value
                        total += value
                        break
                    print("Please enter a value between 0 and 1.")
                except ValueError:
                    print("Invalid number. Please try again.")
        if abs(total - 1.0) > 0.01:
            raise ValueError("Total weight must sum to 1.0")
        self.analysis_weights = new_weights

    async def get_product_details(self) -> JsonData:
        logger.info("Starting product details collection")
        try:
            print("\nEnter Product Details:")
            print("=" * 50)

            self.product_name = input("Product Name: ").strip()

            while True:
                try:
                    self.units_per_shipment = int(input("Units per Shipment: "))
                    if self.units_per_shipment > 0:
                        break
                    print("Please enter a positive number.")
                except ValueError:
                    print("Please enter a valid number.")

            print("\nEnter Dimensions (in cm):")
            while True:
                try:
                    self.dimensions["length"] = float(input("Length: "))
                    self.dimensions["width"] = float(input("Width: "))
                    self.dimensions["height"] = float(input("Height: "))
                    if all(dim > 0 for dim in self.dimensions.values()):
                        break
                    print("All dimensions must be positive numbers.")
                except ValueError:
                    print("Please enter valid numbers.")

            self.packaging_location = input("\nPackaging Location: ").strip()

            while True:
                try:
                    self.budget_constraint = float(input("Budget Constraint ($): "))
                    if self.budget_constraint > 0:
                        break
                    print("Please enter a positive number.")
                except ValueError:
                    print("Please enter a valid number.")

            await self.get_analysis_weights()

            validation_error = await self.validate_product_details()
            if validation_error:
                raise ValueError(validation_error)

            await self.save_to_json()

            response = {
                "product_name": self.product_name,
                "units_per_shipment": self.units_per_shipment,
                "dimensions": self.dimensions,
                "packaging_location": self.packaging_location,
                "budget_constraint": self.budget_constraint,
                "analysis_weights": self.analysis_weights,
                "metadata": {
                    "timestamp": self.timestamp,
                    "user": self.user,
                    "volume": self.calculate_volume(),
                    "status": "success"
                }
            }

            logger.info(f"Successfully collected details for product: {self.product_name}")
            return response

        except ValueError as ve:
            logger.error(f"Validation error: {str(ve)}")
            raise
        except Exception as e:
            logger.error(f"Failed to get product details: {str(e)}", exc_info=True)
            raise

    def calculate_volume(self) -> float:
        return (self.dimensions["length"] *
                self.dimensions["width"] *
                self.dimensions["height"])

    def display_details(self) -> None:
        try:
            logger.info("Displaying product details")
            print("\nProduct Details:")
            print("=" * 50)
            print(f"Product Name: {self.product_name}")
            print(f"Units per shipment: {self.units_per_shipment}")
            print(f"Dimensions (L×W×H): {self.dimensions['length']}×"
                  f"{self.dimensions['width']}×{self.dimensions['height']} cm")
            print(f"Volume: {self.calculate_volume()} cubic cm")
            print(f"Packaging Location: {self.packaging_location}")
            print(f"Budget Constraint: ${self.budget_constraint:.2f}")
            print(f"Timestamp: {self.timestamp}")
            print(f"User: {self.user}")
            print("Analysis Weights:")
            for key, value in self.analysis_weights.items():
                print(f"  {key.capitalize()}: {value:.2f}")
            print("=" * 50)
        except Exception as e:
            logger.error(f"Error displaying details: {str(e)}")

    async def save_to_json(self) -> None:
        logger.info(f"Saving product details to JSON for {self.product_name}")
        try:
            data = {
                "product_name": self.product_name,
                "units_per_shipment": self.units_per_shipment,
                "dimensions": self.dimensions,
                "packaging_location": self.packaging_location,
                "budget_constraint": self.budget_constraint,
                "analysis_weights": self.analysis_weights,
                "metadata": {
                    "timestamp": self.timestamp,
                    "user": self.user,
                    "volume": self.calculate_volume()
                }
            }

            os.makedirs(_settings.reports_dir, exist_ok=True)
            filename = os.path.join(
                _settings.reports_dir,
                f"{self.product_name.lower().replace(' ', '_')}.json",
            )

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: json.dump(data, open(filename, 'w'), indent=4)
            )

            logger.info(f"Successfully saved product details to {filename}")
        except Exception as e:
            logger.error(f"Failed to save product details: {str(e)}", exc_info=True)
            raise

# Main block remains unchanged
