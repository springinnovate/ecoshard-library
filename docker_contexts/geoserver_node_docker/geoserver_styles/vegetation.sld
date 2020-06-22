<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>vegetation</Name>
    <UserStyle>
      <Title>vegetation</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>
              <ColorMapEntry quantity="${env('p0', 0)}" label="${env('p0', 0)}" color="#f9fae5"/>
              <ColorMapEntry quantity="${env('p30', 6)}" label="${env('p30', 6)}" color="#ccd682"/>
              <ColorMapEntry quantity="${env('p60', 12)}" label="${env('p60', 12)}" color="#a6bd34"/>
              <ColorMapEntry quantity="${env('p90', 18)}" label="${env('p90', 18)}" color="#72b416"/>
              <ColorMapEntry quantity="${env('p100', 20)}" label="${env('p100', 20)}" color="#325900"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>