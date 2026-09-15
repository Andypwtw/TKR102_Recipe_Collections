db = db.getSiblingDB(process.env.MONGO_INITDB_DATABASE || "recipe_ai");
db.createCollection("raw_recipes");
db.raw_recipes.createIndex({SEQ: 1}, {unique: true});
