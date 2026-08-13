# crawlers/regional/__init__.py

from .dallas import (
    DallasFedAdapter,
)

from .cleveland import (
    ClevelandFedAdapter,
)

from .minneapolis import (
    MinneapolisFedAdapter,
)

from .chicago import (
    ChicagoFedAdapter,
)

from .boston import (
    BostonFedAdapter,
)

from .kansascity import (
    KansasCityFedAdapter,
)

from .richmond import (
    RichmondFedAdapter,
)

from .stlouis import (
    StLouisFedAdapter,
)

from .newyork import (
    NewYorkFedAdapter,
)

from .philadelphia import (
    PhiladelphiaFedAdapter,
)

from .sanfrancisco import (
    SanFranciscoFedAdapter,
)


# ============================================================
# FED NAME → ADAPTER
#
# fed_members.csv의 "fed" 컬럼 값과
# 아래 key가 정확히 일치해야 함.
# ============================================================

REGIONAL_ADAPTERS = {

    "Dallas Fed":
        DallasFedAdapter,

    "Cleveland Fed":
        ClevelandFedAdapter,

    "Minneapolis Fed":
        MinneapolisFedAdapter,

    "Chicago Fed":
        ChicagoFedAdapter,

    "Boston Fed":
        BostonFedAdapter,

    "Kansas City Fed":
        KansasCityFedAdapter,

    "Richmond Fed":
        RichmondFedAdapter,

    "St. Louis Fed":
        StLouisFedAdapter,

    "New York Fed":
        NewYorkFedAdapter,

    "Philadelphia Fed":
        PhiladelphiaFedAdapter,

    "San Francisco Fed":
        SanFranciscoFedAdapter,
}


__all__ = [
    "DallasFedAdapter",
    "ClevelandFedAdapter",
    "MinneapolisFedAdapter",
    "ChicagoFedAdapter",
    "BostonFedAdapter",
    "KansasCityFedAdapter",
    "RichmondFedAdapter",
    "StLouisFedAdapter",
    "NewYorkFedAdapter",
    "PhiladelphiaFedAdapter",
    "SanFranciscoFedAdapter",
    "REGIONAL_ADAPTERS",
]