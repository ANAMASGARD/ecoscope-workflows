from typing import Annotated

from pydantic import Field

from ecoscope_workflows.decorators import distributed
from ecoscope_workflows.tasks.python.io import SubjectGroupObservationsGDFSchema
from ecoscope_workflows.tasks.python.analysis import TrajectoryGDFSchema
from ecoscope_workflows.types import DataFrame


class RelocationsGDFSchema(SubjectGroupObservationsGDFSchema):
    # FIXME: how does this differ from `SubjectGroupObservationsGDFSchema`?
    pass


def _process_relocations(
    observations: DataFrame[SubjectGroupObservationsGDFSchema],
    /,
    filter_point_coords: Annotated[list[list[float]], Field()],   
    relocs_columns: Annotated[list[str], Field()],
) -> DataFrame[RelocationsGDFSchema]:
    from ecoscope.base import RelocsCoordinateFilter, Relocations
    
    relocs = Relocations(observations)

    # filter relocations based on the config
    relocs.apply_reloc_filter(
        RelocsCoordinateFilter(filter_point_coords=filter_point_coords),
        inplace=True,
    )
    relocs.remove_filtered(inplace=True)

    # subset columns
    relocs = relocs[relocs_columns]

    # rename columns
    relocs.columns = [i.replace("extra__", "") for i in relocs.columns]
    relocs.columns = [i.replace("subject__", "") for i in relocs.columns]
    return relocs


def _relocations_to_trajectory(
    relocations: DataFrame[RelocationsGDFSchema],
    /,
    min_length_meters: Annotated[float, Field()],
    max_length_meters: Annotated[float, Field()],
    max_time_secs: Annotated[float, Field()],
    min_time_secs: Annotated[float, Field()],
    max_speed_kmhr: Annotated[float, Field()],
    min_speed_kmhr: Annotated[float, Field()],
) -> DataFrame[TrajectoryGDFSchema]:
    from ecoscope.base import Relocations
    from ecoscope.base import Trajectory, TrajSegFilter

    # trajectory creation
    traj = Trajectory.from_relocations(Relocations(relocations))

    traj_seg_filter = TrajSegFilter(
        min_length_meters=min_length_meters,
        max_length_meters=max_length_meters,
        min_time_secs=min_time_secs,
        max_time_secs=max_time_secs,
        min_speed_kmhr=min_speed_kmhr,
        max_speed_kmhr=max_speed_kmhr,
    )

    # trajectory filtering
    traj.apply_traj_filter(traj_seg_filter, inplace=True)
    traj.remove_filtered(inplace=True)

    return traj


process_relocations = distributed(_process_relocations)
relocations_to_trajectory = distributed(_relocations_to_trajectory)
