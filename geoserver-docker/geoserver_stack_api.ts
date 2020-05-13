import {
  api,
  body,
  endpoint,
  Float,
  queryParams,
  request,
  response,
  String
  } from "@airtasker/spot";

@api({
  name: "GeoServer STAC API"
})
class Api {}

@endpoint({
  method: "POST",
  path: '/api/v1/publish'
})
class Publish {
  @request
  request(@queryParams
      queryParams: {
        /* API key that has permission to search catalogs */
        api_key: String;
      },
      @body body: PublishRequest) {}

  @response({ status: 200})
  response(@body body: PublishResponse) {}
}

interface PublishRequest {
  /* catalog to publish to */
  catalog: String;
  /* asset ID, must be unique to the catalog. */
  id: String;
  /* mediatype of the raster. Currently only 'GeoTIFF' is supported. */
  mediatype:  String;
  /* uri to the asset that is accessible by this server.
      Currently supports only `gs://`. */
  uri: String;
  /* description of the asset */
  description: String;
  /* (optional) if True, will overwrite existing catalog:id asset */
  force: boolean;
  /* (optional) if present sets the datetime to this string,
      if absent sets the datetime of the asset to the UTC time at
      publishing. String must be formatted as "Y-m-d H:M:S TZ",
      ex: '2018-06-29 17:08:00 UTC'. */
  utc_datetime: String;
  /* if present sets the default style when "fetch"ed by a future REST API
     call. */
  default_style: String;
  /* an arbitrary set of key/value pairs to associate with this asset. */
  attribute_dict: {};
}

interface PublishResponse {
  /* The `callback_url` can be queried for when the asset is published. */
  callback_url: String;
}

@endpoint({
  method: "POST",
  path: "/api/v1/pixel_pick"
})
class PixelPick {
  /* Get the value of an asset pixel from a lat/lng coordinate */
  @request
  request(@body body: PixelPickRequest) {}

  @response({ status: 200})
  response(@body body: PixelPickResponse) {}
}

@endpoint({
  method: "POST",
  path: "/api/v1/fetch"
})
class Fetch {
  /* Fetch wms, preview, or viewer given catalog and asset id */
  @request
  request(@body body: FetchRequest) {}

  @response({ status: 200})
  response(@body body: FetchResponse) {}
}

@endpoint({
  method: "POST",
  path: "/api/v1/search"
})
class Search {
  /* Search for catalog IDs given search params */
  @request
  request(
    @queryParams
      queryParams: {
        /* API key that has permission to search catalogs */
        api_key: String;
      },
    @body body: SearchRequest) {}

  @response({ status: 200})
  response(@body body: SearchResponse) {}
}

interface SearchRequest {
  /* Bounding box is a string in the format "xmin, ymin, xmax, ymax",
     can be empty */
  bounding_box: String;
  /* Comma separated string of catalog lists to search, can be empty */
  catalog_list: String;
  /* Complete or partial asset id, can be empty */
  asset_id: String;
  /* UTC Datetime string bounds, either an exact time "exact_time",
    a range, "low_time/high_time" (separated by /), upper bound "../high_time"
    or lower bound "low_time/.." */
  datetime: String;
  /* Matching anything in the description */
  description: String;
}

interface SearchResponse {
  features: FeatureDescription[];
}

interface FeatureDescription {
  /* Asset ID */
  id: String;
  /* Bounding box list of 4 element floats */
  bbox: Float[];
  /* 'asset description */
  description: String;
  /* Arbitrary object of additional attributes for this asset */
  attribute_dict: {};
}

interface FetchRequest {
  catalog: String;
  asset_id: String;
  /* Type can be one of "preview", "uri", or "wms" */
  type: String;
}

interface FetchResponse {
  /* "WMS" or "uri" depending on body type passed */
  type: String;
  /* url for the specified type */
  link: String;
  /* min stats */
  raster_min: Float;
  /* max stats */
  raster_max: Float;
  /* mean stats */
  raster_mean: Float;
  /*  stdev stats */
  raster_stdev: Float;
}

interface PixelPickRequest {
  catalog: String;
  asset_id: String;
  lng: Float;
  lat: Float;
}

interface PixelPickResponse {
  firstName: string;
  lastName: string;
  role: string;
}
