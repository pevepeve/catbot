from infrastructure.subsplease_client import SubspleaseClient
from repositories.anime_repository import AnimeRepository
from services.anime_service import AnimeService


def get_schedule():
    AnimeService(AnimeRepository(), SubspleaseClient()).refresh_schedule()


if __name__ == "__main__":
    get_schedule()

