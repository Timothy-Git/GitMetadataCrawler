import strawberry

from backend.graphql.mutation import Mutation
from backend.graphql.query import Query

schema = strawberry.Schema(query=Query, mutation=Mutation)
