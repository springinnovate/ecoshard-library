import {
  api,
  endpoint,
  request,
  response,
  body,
  String,
  Float } from "@airtasker/spot";

@api({
  name: "GeoServer STAC API"
})
class Api {}

@endpoint({
  method: "POST",
  path: "/api/v1/pixel_pick"
})
class PixelPick {
  /* Get the value of a pixel from a lat/lng point */
  @request
  request(@body body: PixelPickRequest) {}

  @response({ status: 200})
  response(@body body: PixelPickResponse) {}
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
