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
              <ColorMapEntry color="#000000" quantity="${env('nodata', -9999.0)}" label="${env('nodata', -9999.0)}" opacity="0"/>
              <ColorMapEntry color="#0d0887" quantity="${env('p0', 0.0)}" label="${env('p0', 0.0)}" opacity="1"/>
              <ColorMapEntry color="#5901a5" quantity="${env('p2', 0.02)}" label="${env('p2', 0.02)}" opacity="1"/>
              <ColorMapEntry color="#c43e7f" quantity="${env('p50', 0.5)}" label="${env('p50', 0.5)}" opacity="1"/>
              <ColorMapEntry color="#fcce25" quantity="${env('p98', 0.98)}" label="${env('p98', 0.98)}" opacity="1"/>
              <ColorMapEntry color="#f0f921" quantity="${env('p100', 1.0)}" label="${env('p100', 1.0)}" opacity="1"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>