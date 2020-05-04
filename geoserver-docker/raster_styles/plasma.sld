<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>plasma</Name>
    <UserStyle>
      <Title>plasma</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>
              <ColorMapEntry quantity="${env('p0', 0.0)}" label="${env('p0', 0.0)}" color="#0d0887"/>
              <ColorMapEntry quantity="${env('p2', 0.0)}" label="${env('p2', 0.0)}" color="#5901a5"/>
              <ColorMapEntry quantity="${env('p50', 0.0)}" label="${env('p50', 0.0)}" color="#c43e7f"/>
              <ColorMapEntry quantity="${env('p98', 0.0)}" label="${env('p98', 0.0)}" color="#fcce25"/>
              <ColorMapEntry quantity="${env('p100', 0.0)}" label="${env('p100', 0.0)}" color="#f0f921"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
