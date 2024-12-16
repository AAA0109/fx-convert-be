import graphene
import main.apps.currency.schema
import main.apps.account.schema

class Query(
    main.apps.currency.schema.Query,
    main.apps.account.schema.Query,
    graphene.ObjectType
):
    pass


schema = graphene.Schema(query=Query)
