### Perform updates

Here are updates. Producers and directors certainly hope that those average ratings are on trend.

The `movie_update` field contains an expected `id` argument to identify a record and a `data` field you can use to set values in this update.

```graphql
mutation UpdateMovie(
  $id: UUID!,
  $genre: String!,
  $rating: Int!,
  $description: String!
) {
  movie_update(id: $id,
    data: {
      genre: $genre
      rating: $rating
      description: $description
    })
}
```

To perform multiple updates, use the `movie_updateMany` field.

```graphql
# Multiple updates (increase all ratings of a genre)
mutation IncreaseRatingForGenre($genre: String!, $rating: Int!) {
  movie_updateMany(
    where: { genre: { eq: $genre } },
    data:
      {
        rating: $rating
      })
}
```
