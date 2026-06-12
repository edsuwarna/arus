"""Central model imports for Alembic autodiscovery."""

from arus.shared.db.session import Base  # noqa: F401
from arus.modules.auth.models import User  # noqa: F401
from arus.modules.pipeline.models import Pipeline, PipelineTable, Watermark, TransformScript  # noqa: F401
from arus.modules.pipeline.dead_letter import DeadLetter  # noqa: F401
from arus.modules.pipeline.quality import DataQualityLog  # noqa: F401
from arus.modules.run_log.models import Run, RunTableStat, RunLog  # noqa: F401
from arus.modules.source.models import Source  # noqa: F401
from arus.modules.destination.models import Destination  # noqa: F401
from arus.modules.settings.router import RuntimeSetting  # noqa: F401
from arus.modules.notification.models import NotificationTarget, PipelineNotification  # noqa: F401
