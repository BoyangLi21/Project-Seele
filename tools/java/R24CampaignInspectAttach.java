import com.sun.tools.attach.VirtualMachine;
public final class R24CampaignInspectAttach
{
    public static void main(String[] args)throws Exception
    {
        int matches=0;
        for(var descriptor:VirtualMachine.list())
        {
            if(!descriptor.displayName().contains("BootstrapLauncher"))continue;
            var vm=VirtualMachine.attach(descriptor.id());
            try{if("r24-campaign".equals(vm.getSystemProperties().getProperty("projectseele.regionalBuild"))){vm.loadAgent(args[0],args[1]);matches++;}}
            finally{vm.detach();}
        }
        if(matches!=1)throw new IllegalStateException("Expected exactly one isolated review JVM, found "+matches);
    }
}
