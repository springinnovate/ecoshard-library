<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>weather</Name>
    <UserStyle>
      <Title>weather</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>
              <ColorMapEntry quantity="${env('p0', 0)}" label="${env('p0', 0.0)}" color="#2093BD"/>
              <ColorMapEntry quantity="${env('p25', 1.5)}" label="${env('p25', 1.5)}" color="#9AD94C"/>
              <ColorMapEntry quantity="${env('p50', 3)}" label="${env('p50', 3.0)}" color="#E8E84C"/>
              <ColorMapEntry quantity="${env('p75', 4.5)}" label="${env('p75', 4.5)}" color="#FDC591"/>
              <ColorMapEntry quantity="${env('p100', 6)}" label="${env('p100', 6.0)}" color="#E34649"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>