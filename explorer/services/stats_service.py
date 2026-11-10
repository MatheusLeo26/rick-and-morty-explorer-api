"""
Analytical statistics service using Pandas over locally stored SQLite favorites.
"""
from typing import Any

import pandas as pd

from explorer.models import FavoriteCharacter, FavoriteEpisode


class StatsService:
    """
    Computes descriptive and categorical statistics on favorite characters using Pandas.
    """

    @staticmethod
    def compute_favorites_stats(
        status: str | None = None,
        species: str | None = None,
    ) -> dict[str, Any]:
        """
        Loads favorite characters from SQLite into a Pandas DataFrame and computes:
        - Total counts
        - Distribution and percentages by status, species, and gender
        - Top origins and locations
        - Episode participation metrics (mean, median, min, max, sum, most/least featured)
        - Cross-tabulation of species by status
        """
        queryset = FavoriteCharacter.objects.all()
        if status:
            queryset = queryset.filter(status__iexact=status.strip())
        if species:
            queryset = queryset.filter(species__icontains=species.strip())

        records = list(
            queryset.values(
                "external_id",
                "name",
                "status",
                "species",
                "gender",
                "origin_name",
                "location_name",
                "episode_count",
                "episode_urls",
            )
        )
        total_fav_episodes = FavoriteEpisode.objects.count()
        filters_applied = {
            "status": status.strip() if status else None,
            "species": species.strip() if species else None,
        }

        if not records:
            return {
                "total_favorites": 0,
                "total_favorite_episodes": total_fav_episodes,
                "filters_applied": filters_applied,
                "by_status": {},
                "status_percentage": {},
                "by_species": {},
                "by_gender": {},
                "top_origins": {},
                "top_locations": {},
                "episode_stats": {
                    "mean_episodes_per_character": 0.0,
                    "median_episodes_per_character": 0.0,
                    "max_episodes": 0,
                    "min_episodes": 0,
                    "total_episode_appearances": 0,
                    "unique_episodes_across_favorites": 0,
                    "most_featured_character": None,
                    "least_featured_character": None,
                },
                "species_by_status": {},
            }

        df = pd.DataFrame(records)

        # Categorical distributions using Pandas value_counts
        by_status = {str(k): int(v) for k, v in df["status"].value_counts().items()}
        status_pct = {
            str(k): float(round(v * 100.0, 2))
            for k, v in df["status"].value_counts(normalize=True).items()
        }
        by_species = {str(k): int(v) for k, v in df["species"].value_counts().items()}
        by_gender = {str(k): int(v) for k, v in df["gender"].value_counts().items()}
        top_origins = {str(k): int(v) for k, v in df["origin_name"].value_counts().head(5).items()}
        top_locations = {
            str(k): int(v) for k, v in df["location_name"].value_counts().head(5).items()
        }

        # Numerical aggregations on episode_count using Pandas
        ep_series = df["episode_count"].astype(int)
        mean_ep = float(round(ep_series.mean(), 2))
        median_ep = float(round(ep_series.median(), 2))
        max_ep = int(ep_series.max())
        min_ep = int(ep_series.min())
        sum_ep = int(ep_series.sum())

        # Unique episodes across all favorite characters
        unique_episodes: set[str] = set()
        for ep_list in df["episode_urls"]:
            if isinstance(ep_list, list):
                unique_episodes.update(ep_list)

        # Most and least featured characters using DataFrame sorting
        sorted_desc = df.sort_values(by=["episode_count", "external_id"], ascending=[False, True])
        most_row = sorted_desc.iloc[0]
        sorted_asc = df.sort_values(by=["episode_count", "external_id"], ascending=[True, True])
        least_row = sorted_asc.iloc[0]

        # Cross-tabulation of species vs status using Pandas crosstab
        crosstab_df = pd.crosstab(df["species"], df["status"])
        species_by_status = {
            str(species_key): {str(st_key): int(val) for st_key, val in row.items()}
            for species_key, row in crosstab_df.to_dict(orient="index").items()
        }

        return {
            "total_favorites": int(len(df)),
            "total_favorite_episodes": total_fav_episodes,
            "filters_applied": filters_applied,
            "by_status": by_status,
            "status_percentage": status_pct,
            "by_species": by_species,
            "by_gender": by_gender,
            "top_origins": top_origins,
            "top_locations": top_locations,
            "episode_stats": {
                "mean_episodes_per_character": mean_ep,
                "median_episodes_per_character": median_ep,
                "max_episodes": max_ep,
                "min_episodes": min_ep,
                "total_episode_appearances": sum_ep,
                "unique_episodes_across_favorites": len(unique_episodes),
                "most_featured_character": {
                    "external_id": int(most_row["external_id"]),
                    "name": str(most_row["name"]),
                    "episode_count": int(most_row["episode_count"]),
                },
                "least_featured_character": {
                    "external_id": int(least_row["external_id"]),
                    "name": str(least_row["name"]),
                    "episode_count": int(least_row["episode_count"]),
                },
            },
            "species_by_status": species_by_status,
        }
