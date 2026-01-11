package org.onosproject.lldpapp;

import org.onosproject.core.ApplicationId;
import org.onosproject.core.CoreService;
import org.onosproject.store.service.StorageService;
import org.onosproject.net.DeviceService;
import org.onosproject.net.packet.PacketService;
import org.onosproject.app.Application;
import org.onosproject.app.AppComponent;
import org.osgi.framework.BundleContext;
import org.osgi.framework.ServiceReference;

public class LldpAppActivator implements AppComponent {

    private ApplicationId appId;
    private LldpApp lldpApp;

    @Override
    public void activate(BundleContext context) {
        // Registering the application
        appId = coreService.registerApplication("org.onosproject.lldpapp");
        
        // Initializing your application
        lldpApp = new LldpApp();
        lldpApp.activate();
        
        // Registering services
        context.registerService(Application.class.getName(), lldpApp, null);
    }

    @Override
    public void deactivate(BundleContext context) {
        lldpApp.deactivate();
        context.ungetService(appId);
    }
}
